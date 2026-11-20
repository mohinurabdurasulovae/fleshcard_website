"""Run with:  cd backend && python -m pytest -q   (uses a throw-away SQLite database)."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["DATA_DIR"] = _tmp

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.processing.extract import extract_latex, extract_markdown  # noqa: E402
from app.processing.flashcards import generate_cards  # noqa: E402

LATEX = r"""
\documentclass{article}
\newcommand{\coursetitle}{Thermal Physics}
\title{\coursetitle}
\author{A. Student}
\begin{document}
\section{Entropy}
\begin{definition}[Entropy]
The \emph{entropy} of a system is defined as
\[ S = k_B \ln \Omega \]
where $\Omega$ is the number of microstates.
\end{definition}
Heat flows from hot to cold because the total entropy increases.
The difference between work and heat is that work is ordered energy transfer.
\section{Temperature}
The temperature is given by
\begin{equation} \frac{1}{T} = \frac{\partial S}{\partial E} \end{equation}
\end{document}
"""

MARKDOWN = """# CS240

## Heaps
A **heap** is a tree-based data structure that satisfies the heap property.
Unlike a binary search tree, a heap only orders parents relative to children.

## Hashing
A **hash table** is an array of buckets indexed by a hash function.
"""


def test_latex_extraction_and_cards():
    ex = extract_latex(LATEX)
    assert ex.title == "Thermal Physics"
    assert [s["title"] for s in ex.sections][-2:] == ["Entropy", "Temperature"]
    assert "$$S = k_B \\ln \\Omega$$" in ex.text
    cards = generate_cards(ex.text, ex.sections)
    types = {c.card_type for c in cards}
    assert {"definition", "formula"} <= types
    for c in cards:  # every card points at a real passage
        assert 0 <= c.start < c.end <= len(ex.text)


def test_markdown_cards():
    ex = extract_markdown(MARKDOWN)
    qs = [c.question for c in generate_cards(ex.text, ex.sections)]
    assert any("heap" in q.lower() for q in qs)
    assert any("hash table" in q.lower() for q in qs)


def test_api_upload_evaluate_and_stats():
    with TestClient(app) as client:
        meta = client.get("/api/meta").json()
        assert len(meta["criteria"]) >= 5 and meta["rating_scale"][0]["label"] == "Excellent"
        r = client.post("/api/documents/upload", files={"file": ("notes.md", MARKDOWN * 8)},
                        data={"subject": "Computer Science", "title": "Test notes"})
        assert r.status_code == 200, r.text
        doc = r.json()
        cards = client.get(f"/api/flashcards?document_id={doc['id']}").json()["items"]
        assert cards
        r = client.post("/api/evaluations", json={"flashcard_id": cards[0]["id"], "overall": 1,
                                                  "criteria": {"accuracy": 2}, "comment": "ok", "evaluator": "t"})
        assert r.status_code == 200
        stats = client.get("/api/stats/overview").json()
        assert stats["summary"]["student"]["evaluations"] == 1
        assert stats["summary"]["student"]["mean_score"] == 5
        assert client.get("/api/stats/export?format=csv").text.count("\n") >= 2
        assert client.get(f"/api/documents/{doc['id']}/content").json()["sections"]
