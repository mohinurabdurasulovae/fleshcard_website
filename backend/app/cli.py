"""Terminal interface for the data-collection pipeline.

Examples
  python -m app.cli init
  python -m app.cli sources
  python -m app.cli collect                                   # everything enabled
  python -m app.cli collect --subjects Physics --sources willoughby-seago uco16-partiii
  python -m app.cli collect --sources mit-ocw --max-per-course 5
  python -m app.cli retry
  python -m app.cli regenerate --ai
  python -m app.cli export --format csv --out evaluations.csv
"""

import argparse
import sys

from sqlalchemy import select

from .db import SessionLocal
from .jobs import create_job, run_job
from .main import init_db
from .models import Source
from .seed import SUBJECTS

ALIASES = {"cs": "Computer Science", "computer science": "Computer Science", "physics": "Physics",
           "phys": "Physics", "biology": "Biology", "bio": "Biology"}


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create tables and seed sources/topics")
    sub.add_parser("sources", help="list configured sources")
    c = sub.add_parser("collect", help="discover, download and process documents")
    c.add_argument("--subjects", nargs="*", default=[], help="e.g. cs physics biology")
    c.add_argument("--sources", nargs="*", default=[], help="source keys (see `sources`)")
    c.add_argument("--max-per-source", type=int, default=0)
    c.add_argument("--max-per-course", type=int, default=8, help="MIT OCW: lecture-note PDFs per course")
    c.add_argument("--no-flashcards", action="store_true")
    c.add_argument("--no-discover", action="store_true", help="MIT OCW: only use the starter catalogue")
    c.add_argument("--ai", action="store_true", help="use the configured LLM for flashcards")
    c.add_argument("--force", action="store_true", help="re-process documents already collected")
    sub.add_parser("retry", help="retry failed downloads")
    r = sub.add_parser("regenerate", help="regenerate flashcards for all documents")
    r.add_argument("--ai", action="store_true")
    e = sub.add_parser("export", help="export evaluations")
    e.add_argument("--format", choices=["csv", "json"], default="csv")
    e.add_argument("--scope", choices=["evaluations", "summary"], default="evaluations")
    e.add_argument("--out", default="")
    args = p.parse_args(argv)

    init_db()
    db = SessionLocal()
    if args.cmd == "init":
        print("Database ready.")
    elif args.cmd == "sources":
        for s in db.scalars(select(Source).order_by(Source.category, Source.key)).all():
            print(f"{s.key:22} {s.category:8} {s.kind:8} {', '.join(s.subjects):40} {s.url}")
    elif args.cmd == "collect":
        subjects = [ALIASES.get(x.lower(), x) for x in args.subjects]
        bad = [x for x in subjects if x not in SUBJECTS]
        if bad:
            sys.exit(f"Unknown subject(s): {bad}. Choose from {SUBJECTS}")
        job = create_job(db, "collect", subjects or SUBJECTS, args.sources, {
            "max_docs_per_source": args.max_per_source, "max_docs_per_course": args.max_per_course,
            "generate_flashcards": not args.no_flashcards, "use_ai": args.ai, "force": args.force,
            "discover": not args.no_discover})
        run_job(job.id, echo=True)
    elif args.cmd == "retry":
        job = create_job(db, "retry", [], [], {"generate_flashcards": True})
        run_job(job.id, echo=True)
    elif args.cmd == "regenerate":
        job = create_job(db, "regenerate", [], [], {"use_ai": args.ai})
        run_job(job.id, echo=True)
    elif args.cmd == "export":
        from .routers.stats import export
        resp = export(format=args.format, scope=args.scope, evaluator=None, subject=None, db=db)
        out = args.out or f"{args.scope}.{args.format}"
        with open(out, "wb") as f:
            f.write(resp.body)
        print(f"Wrote {out}")
    db.close()


if __name__ == "__main__":
    main()
