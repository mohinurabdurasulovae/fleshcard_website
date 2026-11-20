# NoteCards: lecture notes & flashcards

NoteCards collects university lecture notes from **MIT OpenCourseWare** and **student-written notes** (websites and GitHub repositories) for **Computer Science, Physics and Biology**. It extracts the text, organises it by topic, generates flashcards that link back to the exact passage, and lets you **rate the flashcards** to compare MIT-based and student-based cards.

| Layer | Stack |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, shadcn-style components (Radix), Recharts, KaTeX |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2 |
| Database | PostgreSQL (SQLite also works for a quick try) |
| Collection | Git (sparse clones), httpx + BeautifulSoup crawler, pypdf |

No API key is needed for browsing, collecting, searching, generating flashcards (rule-based) or evaluating. LLM generation is optional.

---

## 1. Quick start

You need **Python 3.11+**, **Node 18.18+**, **git** and **PostgreSQL** (or Docker).

### Database

```bash
docker compose up -d
```

(Or use any PostgreSQL server and create a database named `notesdb`.)

### Backend (API on http://localhost:8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # edit DATABASE_URL if needed
python -m app.cli init           # creates tables, seeds sources, MIT catalogue and topics
uvicorn app.main:app --reload --port 8000
```

> To try it without PostgreSQL, set `DATABASE_URL=sqlite:///./data/notes.db` in `backend/.env`.

### Frontend (website on http://localhost:3000)

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api/*` to the backend. Set `API_URL` in `frontend/.env.local` if the API is not on `http://127.0.0.1:8000`.

---

## 2. Collecting data

Collection runs from the **Data Collection** page (pick subjects and sources, watch progress, retry failures) or from the terminal:

```bash
cd backend
python -m app.cli sources                                   # list sources and their keys
python -m app.cli collect                                   # every enabled source, all subjects
python -m app.cli collect --subjects physics                # one subject
python -m app.cli collect --sources mit-ocw --max-per-course 5
python -m app.cli collect --sources willoughby-seago uco16-partiii dexter-chua
python -m app.cli retry                                     # retry failed downloads
python -m app.cli regenerate                                # rebuild flashcards (rated cards are kept)
python -m app.cli export --format csv --out evaluations.csv # export ratings
```

### Sources

| Key | Source | Method |
|---|---|---|
| `mit-ocw` | MIT OpenCourseWare | Discovers courses (MIT Learn API plus a 28-course starter catalogue), opens each course's *Lecture Notes* page and downloads the PDFs |
| `anthony-zhang` | anthony-zhang.me/University-Notes | GitHub mirror `Uberi/University-Notes` (Markdown + LaTeX) |
| `bencuan` | notes.bencuan.me | Website crawler |
| `jonas-devlieghere` | jonasdevlieghere.com/post/course-notes | Website crawler (PDF links) |
| `rosikand` | rosikand.github.io/notes | GitHub mirror `rosikand/notes` |
| `willoughby-seago` | WilloughbySeago/Uni-Notes | GitHub (LaTeX, `\input` resolved) |
| `uco16-partiii` | uco16/partiii-notes | GitHub (LaTeX) |
| `ucdavis-lim` | lim.physics.ucdavis.edu lecture notes | Website crawler (PDF links) |
| `dexter-chua` | dec41.user.srcf.net/notes | GitHub mirror `dalcde/cam-notes` (physics-related courses) |
| `thepiedpieper` | thepiedpieper.github.io/notes | GitHub mirror of the site (HTML + PDF) |
| `bahanonu-bio42` | bahanonu.com Bio 42 notes | Direct PDF |
| `ucla-adeshpande` | adeshpande3/UCLA-Course-Notes (CS 111 + LS 7A/B/C) | GitHub |

Add or edit sources in `backend/app/seed.py`. They are upserted whenever the API starts or you run `python -m app.cli init`.

**Copyright and access.** Every document keeps its original URL, author and licence; the licence is read from the repository's `LICENSE` file when one exists, otherwise it is marked *no explicit licence*. The crawler identifies itself, honours `robots.txt` and rate-limits requests (`REQUEST_DELAY_SECONDS`). Only publicly accessible material is fetched, and every page links back to the original. Use the data for non-commercial educational research. Admins can reject documents in *Review documents* to hide them.

### Supported formats

PDF (`pypdf`, with per-page sections), HTML (main-content extraction, KaTeX/MathJax maths preserved), Markdown and LaTeX. For LaTeX, `\input`/`\include` are resolved, theorem/definition environments are kept, maths is preserved for KaTeX and custom `\newcommand` macros are passed to the renderer. Scanned PDFs without a text layer are skipped (no OCR).

---

## 3. What the website does

- **Dashboard:** totals, MIT vs student split, subject distribution, card types, recently added documents, popular topics.
- **Explore Courses:** search and filter by subject, university, source and MIT/student; each course has a detail page.
- **Lecture Notes:** full-text search and a reader with a table of contents, topics per section and the original file (PDF/HTML preview). A side panel lists the flashcards for the current section. *Find answer in the notes* jumps to and highlights the exact passage behind a card. Quiz mode hides answers.
- **Topic Explorer:** automatic topic taxonomy per subject, showing MIT and student coverage side by side, matched sections and related topics. *Matching sections* lists section headings that appear in two or more sources.
- **Flashcards:** separate MIT and student decks (per document, topic or course), flip cards, shuffle and keyboard shortcuts. Every card shows its source, section and page. You can generate cards from any document.
- **Evaluation:** an overall rating on a five-level scale (1 Excellent, 2 Very Good, 3 Acceptable, 4 Poor, 5 Unacceptable), plus an independent rating per research criterion and an optional comment. Blind mode hides the MIT/student label. Ratings are saved per evaluator name.
- **Statistics:** MIT vs student mean scores, rating distribution, criteria radar and table, breakdowns by card type, subject, generator and source, per-document results, a timeline, comments, and a Mann–Whitney U test. CSV and JSON exports are available for both ratings and the summary.
- **Data Collection (admin):** start and stop jobs, live progress and logs, retry failed downloads, approve, reject, edit or delete documents, regenerate flashcards, manage courses and upload files.

### Research quality criteria

Defined in `backend/app/criteria.py`; edit that file to change them. Defaults: factual accuracy, source faithfulness, clarity, relevance, completeness, atomicity, difficulty appropriateness and learning usefulness. Scores are reported as `6 − level`, so 5 is Excellent and 1 is Unacceptable.

### Flashcard generation

- **Rule-based (default, no key).** Produces definitions (definition environments, bold terms, "X is defined as …"), concepts (theorems, laws, section key ideas), explanations ("… because …"), formulas (display equations with their lead-in sentence) and comparisons ("difference between …", "unlike …", "whereas …"). Each card stores the character span, section and page of its source passage.
- **AI (optional).** Set these in `backend/.env`:

  ```bash
  AI_PROVIDER=anthropic          # or: openai  (any OpenAI-compatible server, e.g. Ollama)
  ANTHROPIC_API_KEY=...
  ANTHROPIC_MODEL=claude-sonnet-5-5
  # OPENAI_BASE_URL=http://localhost:11434/v1  OPENAI_MODEL=llama3.1
  ```

  *Generate with AI* buttons then appear. AI cards are tagged with their generator, so statistics can compare rule-based and AI cards.

---

## 4. Project layout

```
backend/
  app/
    main.py            FastAPI app (creates tables + seeds on startup)
    cli.py             terminal commands (collect, retry, regenerate, export)
    models.py          Source, Course, Document, Topic, Flashcard, Evaluation, CollectionJob
    seed.py            sources, MIT starter catalogue, topic taxonomy
    criteria.py        rating scale + research criteria
    collectors/        mit_ocw.py, github_repo.py, website.py (+ direct PDF)
    processing/        extract.py, flashcards.py, topics.py, ai.py
    pipeline.py        candidate -> stored document -> topics -> flashcards
    jobs.py            background job runner
    routers/           catalog, documents, topics, flashcards+evaluations, stats, admin
  tests/               pytest (SQLite)
frontend/
  app/                 dashboard, courses, notes, topics, flashcards, evaluate, statistics, admin
  components/          app shell, rich text (KaTeX + highlight), flashcard, UI primitives
  lib/                 API client, types, colour system
```

API docs: http://localhost:8000/docs

## 5. Tests

```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q
cd frontend && npm run typecheck && npm run build
```
