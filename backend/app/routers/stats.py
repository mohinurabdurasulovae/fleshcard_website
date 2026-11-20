import math
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..criteria import CARD_TYPES, CRITERIA, LEVEL_LABEL, level_to_score
from ..db import get_db
from ..models import Document, Evaluation, Flashcard
from .flashcards import _export

router = APIRouter(prefix="/api/stats", tags=["statistics"])
CATS = ("mit", "student")


def _mean(xs):
    return round(sum(xs) / len(xs), 3) if xs else None


def _sd(xs):
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return round(math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)), 3)


def mann_whitney(a: list[float], b: list[float]) -> dict | None:
    """Two-sided Mann–Whitney U test (normal approximation with tie correction)."""
    n1, n2 = len(a), len(b)
    if n1 < 3 or n2 < 3:
        return None
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks = [0.0] * len(allv)
    i = 0
    ties = 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        t = j - i + 1
        ties += t ** 3 - t
        i = j + 1
    r1 = sum(r for r, (_, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    n = n1 + n2
    sigma = math.sqrt(n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1))))
    if sigma == 0:
        return {"u": u1, "z": 0.0, "p_value": 1.0, "effect_size_r": 0.0}
    z = (u1 - mu) / sigma
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"u": round(u1, 1), "z": round(z, 3), "p_value": round(p, 4), "effect_size_r": round(abs(z) / math.sqrt(n), 3)}


def _rows(db: Session, evaluator: str | None, subject: str | None):
    stmt = (select(Evaluation).join(Evaluation.flashcard)
            .options(selectinload(Evaluation.flashcard).selectinload(Flashcard.document).selectinload(Document.source),
                     selectinload(Evaluation.flashcard).selectinload(Flashcard.document).selectinload(Document.course),
                     selectinload(Evaluation.flashcard).selectinload(Flashcard.topic)))
    if evaluator:
        stmt = stmt.where(Evaluation.evaluator == evaluator)
    if subject:
        stmt = stmt.where(Flashcard.subject == subject)
    return db.scalars(stmt.order_by(Evaluation.created_at)).all()


@router.get("/overview")
def overview(evaluator: str | None = None, subject: str | None = None, db: Session = Depends(get_db)):
    evals = _rows(db, evaluator, subject)
    by_cat = {c: [] for c in CATS}
    for e in evals:
        by_cat[e.flashcard.category].append(e)

    summary = {}
    for cat, es in by_cat.items():
        scores = [level_to_score(e.overall) for e in es]
        dist = {lvl: 0 for lvl in range(1, 6)}
        for e in es:
            dist[e.overall] += 1
        total_cards = db.scalar(select(func.count()).select_from(Flashcard).where(
            Flashcard.category == cat, *( [Flashcard.subject == subject] if subject else [])))
        summary[cat] = {
            "evaluations": len(es), "cards_rated": len({e.flashcard_id for e in es}), "total_cards": total_cards,
            "mean_score": _mean(scores), "sd": _sd(scores),
            "pct_positive": round(100 * sum(1 for e in es if e.overall <= 2) / len(es), 1) if es else None,
            "pct_negative": round(100 * sum(1 for e in es if e.overall >= 4) / len(es), 1) if es else None,
            "distribution": [{"level": lvl, "label": LEVEL_LABEL[lvl], "count": n,
                              "pct": round(100 * n / len(es), 1) if es else 0} for lvl, n in dist.items()],
        }

    criteria = []
    for c in CRITERIA:
        row = {"key": c["key"], "label": c["label"]}
        for cat in CATS:
            vals = [level_to_score(e.criteria[c["key"]]) for e in by_cat[cat] if (e.criteria or {}).get(c["key"])]
            row[cat] = _mean(vals)
            row[f"{cat}_n"] = len(vals)
        criteria.append(row)

    def group(keyfn, labels=None):
        acc = defaultdict(lambda: {c: [] for c in CATS})
        for e in evals:
            acc[keyfn(e)][e.flashcard.category].append(level_to_score(e.overall))
        keys = labels or sorted(acc)
        return [{"key": k, "mit": _mean(acc[k]["mit"]), "student": _mean(acc[k]["student"]),
                 "mit_n": len(acc[k]["mit"]), "student_n": len(acc[k]["student"])} for k in keys]

    by_type = group(lambda e: e.flashcard.card_type, [t["key"] for t in CARD_TYPES])
    by_subject = group(lambda e: e.flashcard.subject)
    by_generator = group(lambda e: e.flashcard.generator.split("+")[0].split(":")[0])

    src = defaultdict(list)
    src_cat = {}
    for e in evals:
        name = e.flashcard.document.source.name
        src[name].append(level_to_score(e.overall))
        src_cat[name] = e.flashcard.category
    by_source = sorted([{"source": k, "category": src_cat[k], "mean": _mean(v), "n": len(v)} for k, v in src.items()],
                       key=lambda x: -(x["mean"] or 0))

    docs = defaultdict(list)
    doc_info = {}
    for e in evals:
        d = e.flashcard.document
        docs[d.id].append(e)
        doc_info[d.id] = {"id": d.id, "title": d.title, "category": d.category, "subject": d.subject,
                          "source": d.source.name, "course": d.course.code if d.course else ""}
    by_document = []
    for did, es in docs.items():
        crit_means = {}
        for c in CRITERIA:
            vals = [level_to_score(e.criteria[c["key"]]) for e in es if (e.criteria or {}).get(c["key"])]
            crit_means[c["key"]] = _mean(vals)
        by_document.append({**doc_info[did], "n": len(es), "cards": len({e.flashcard_id for e in es}),
                            "mean": _mean([level_to_score(e.overall) for e in es]), "criteria": crit_means})
    by_document.sort(key=lambda x: (-(x["mean"] or 0), -x["n"]))

    timeline = defaultdict(lambda: {"mit": 0, "student": 0})
    for e in evals:
        timeline[e.created_at.date().isoformat()][e.flashcard.category] += 1
    timeline_out = [{"date": k, **v} for k, v in sorted(timeline.items())]

    mit_scores = [level_to_score(e.overall) for e in by_cat["mit"]]
    stu_scores = [level_to_score(e.overall) for e in by_cat["student"]]
    test = mann_whitney(mit_scores, stu_scores)
    pref = None
    if mit_scores and stu_scores:
        diff = round(_mean(mit_scores) - _mean(stu_scores), 3)
        pref = {"preferred": "mit" if diff > 0 else "student" if diff < 0 else "tie", "difference": diff,
                "significant": bool(test and test["p_value"] < 0.05)}

    comments = [{"id": e.id, "comment": e.comment, "overall": e.overall, "category": e.flashcard.category,
                 "question": e.flashcard.question, "evaluator": e.evaluator, "created_at": e.created_at.isoformat()}
                for e in reversed(evals) if e.comment][:20]
    evaluators = [r for (r,) in db.execute(select(Evaluation.evaluator).distinct())]
    return {"summary": summary, "criteria": criteria, "by_type": by_type, "by_subject": by_subject,
            "by_generator": by_generator, "by_source": by_source, "by_document": by_document[:100],
            "timeline": timeline_out, "test": test, "preference": pref, "comments": comments,
            "evaluators": evaluators, "total_evaluations": len(evals)}


@router.get("/export")
def export(format: str = "csv", scope: str = "evaluations", evaluator: str | None = None,
           subject: str | None = None, db: Session = Depends(get_db)):
    if scope == "summary":
        data = overview(evaluator, subject, db)
        if format == "json":
            return _export([data], "json", "summary")
        rows = []
        for cat in CATS:
            s = data["summary"][cat]
            rows.append({"group": "overall", "key": cat, "mean_score": s["mean_score"], "n": s["evaluations"]})
        for c in data["criteria"]:
            for cat in CATS:
                rows.append({"group": "criterion", "key": f"{c['key']}:{cat}", "mean_score": c[cat], "n": c[f"{cat}_n"]})
        for g in ("by_type", "by_subject", "by_generator"):
            for r in data[g]:
                for cat in CATS:
                    rows.append({"group": g, "key": f"{r['key']}:{cat}", "mean_score": r[cat], "n": r[f"{cat}_n"]})
        return _export(rows, "csv", "summary")

    rows = []
    for e in _rows(db, evaluator, subject):
        c = e.flashcard
        d = c.document
        row = {"evaluation_id": e.id, "created_at": e.created_at.isoformat(), "evaluator": e.evaluator,
               "flashcard_id": c.id, "category": c.category, "subject": c.subject, "card_type": c.card_type,
               "generator": c.generator, "source": d.source.name, "course": d.course.code if d.course else "",
               "document_id": d.id, "document_title": d.title, "document_url": d.url, "section": c.section_title,
               "page": c.page, "topic": c.topic.name if c.topic else "", "question": c.question, "answer": c.answer,
               "overall_level": e.overall, "overall_label": LEVEL_LABEL[e.overall], "overall_score": level_to_score(e.overall)}
        for cr in CRITERIA:
            lvl = (e.criteria or {}).get(cr["key"])
            row[f"{cr['key']}_level"] = lvl
            row[f"{cr['key']}_score"] = level_to_score(lvl) if lvl else None
        row["comment"] = e.comment
        rows.append(row)
    extra = {"exported_at": datetime.now(timezone.utc).isoformat(),
             "scale": "level 1=Excellent … 5=Unacceptable; score = 6 - level", "criteria": CRITERIA}
    return _export(rows, format, "evaluations", extra if format == "json" else None)
