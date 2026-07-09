"""dera_state.py — checkpoint / resume state manager for the DERA-ZN pipeline.

Deterministic, stdlib-only. This is the "resume engine": each stage hashes its
inputs and records completion in outputs/<order_id>/state.json. A stage is
skipped (reused) only when it is `done` AND its input hash is unchanged, so a
crashed or partial run resumes at the first incomplete/changed stage.

See docs/dera_framework.md for the resume contract.

Library API:
    load_state / save_state / new_state
    hash_inputs(*parts)        -> sha256 hex over the stage's inputs
    should_run(state, stage, h)-> True if the stage must (re)compute
    mark_done(state, stage, file, h, now=?)
    reset_stage(state, stage)

CLI:
    py tools/dera_state.py show  <order_id>
    py tools/dera_state.py reset <order_id> [stage]
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

# The four DERA-ZN stages, in order.
STAGES = ("detect", "evaluate", "recommend", "act")


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def outputs_root(root=None):
    return os.path.join(root or _repo_root(), "outputs")


def order_dir(order_id, root=None):
    return os.path.join(outputs_root(root), order_id)


def state_path(order_id, root=None):
    return os.path.join(order_dir(order_id, root), "state.json")


# --------------------------------------------------------------------------- #
# Time (injectable so tests / resumable runs stay deterministic)
# --------------------------------------------------------------------------- #
def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
def new_state(order_id):
    return {
        "order_id": order_id,
        "updated": None,
        "stages": {s: {"status": "todo", "file": None, "input_hash": None} for s in STAGES},
    }


def load_state(order_id, root=None):
    """Load the order's state, or a fresh todo-state if none exists yet."""
    path = state_path(order_id, root)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return new_state(order_id)


def save_state(state, root=None, now=None):
    """Persist state to outputs/<order_id>/state.json, stamping `updated`."""
    state["updated"] = now or utc_now_iso()
    d = order_dir(state["order_id"], root)
    os.makedirs(d, exist_ok=True)
    with open(state_path(state["order_id"], root), "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
    return state


# --------------------------------------------------------------------------- #
# Hashing + resume decision
# --------------------------------------------------------------------------- #
def hash_inputs(*parts):
    """Stable sha256 over the JSON-normalized inputs of a stage.

    A stage's inputs typically include: the relevant CSV rows, the outputs of
    upstream stages, and the business parameters used. Because upstream outputs
    are part of the hash, recomputing an upstream stage changes downstream
    hashes too — downstream stages correctly re-run without any explicit
    cascade logic.
    """
    h = hashlib.sha256()
    for part in parts:
        h.update(json.dumps(part, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
        h.update(b"\x00")  # delimiter so ("a","b") != ("ab",)
    return h.hexdigest()


def _check_stage(stage):
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {STAGES}")


def should_run(state, stage, input_hash):
    """True when the stage must (re)compute: not done, or inputs changed."""
    _check_stage(stage)
    st = state["stages"][stage]
    return not (st["status"] == "done" and st["input_hash"] == input_hash)


def mark_done(state, stage, file, input_hash, now=None):
    """Record a stage as completed with its output file and input hash."""
    _check_stage(stage)
    state["stages"][stage] = {"status": "done", "file": file, "input_hash": input_hash}
    state["updated"] = now or utc_now_iso()
    return state


def reset_stage(state, stage):
    """Mark a stage (back) to todo — forces recompute on the next run."""
    _check_stage(stage)
    state["stages"][stage] = {"status": "todo", "file": None, "input_hash": None}
    return state


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cli(argv=None):
    p = argparse.ArgumentParser(description="Inspect / reset DERA-ZN run state.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("show", help="print an order's state.json")
    ps.add_argument("order_id")

    pr = sub.add_parser("reset", help="reset all stages (or one) back to todo")
    pr.add_argument("order_id")
    pr.add_argument("stage", nargs="?", help="optional single stage to reset")

    args = p.parse_args(argv)
    state = load_state(args.order_id)

    if args.cmd == "show":
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "reset":
        targets = [args.stage] if args.stage else list(STAGES)
        for s in targets:
            reset_stage(state, s)
        save_state(state)
        print(f"reset {targets} for {args.order_id}")
        return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
