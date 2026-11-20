"""Inspect one score or replay one synthetic profile edit without a key."""
import argparse
from contextlib import closing

import relate

from .demo import rank, replay, score_changes, score_job


def show_evidence(row):
    facts = row["f"]
    print(f"  {facts['path']}")
    for hop in facts["hops"]:
        print(f"  {hop['text']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    why = commands.add_parser("why")
    why.add_argument("job")
    feedback = commands.add_parser("replay")
    feedback.add_argument("job")
    feedback.add_argument("verdict")
    args = parser.parse_args()
    try:
        with closing(relate.connect("jobradar.rl", read_only=True)) as db:
            if args.command == "why":
                row = score_job(db, args.job)
                print(f"{args.job} score {row['score']}")
                for label, points in row["parts"]:
                    print(f"  {points:+d} {label}")
                subtotal = sum(points for _, points in row["parts"])
                if subtotal != row["score"]:
                    print(f"  {subtotal} capped to {row['score']}")
                show_evidence(row)
                return
            base = rank(db)
        after = replay("jobradar.rl", args.job, args.verdict)
    except KeyError:
        parser.error(f"unknown JOB {args.job!r}")
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Replay {args.job} {args.verdict}")
    changes = list(score_changes(base, after))
    for old, new in changes:
        print(f"{new['f']['job']} {old['score']} -> {new['score']}")
        print("Before")
        show_evidence(old)
        print("After")
        show_evidence(new)
    if not changes:
        print("No scores changed.")


if __name__ == "__main__":
    main()
