"""MIT OpenCourseWare collector.

1. Discovery – asks the public MIT Learn catalogue API for OCW courses per subject
   (best effort) and merges them with the starter catalogue stored in the database.
2. For every course it opens the course home page (metadata), finds the "Lecture Notes"
   page(s) and follows each resource link to its PDF download.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from sqlalchemy import select

from ..models import Course
from ..seed import OCW_LICENSE
from .base import Candidate, Collector

LEARN_API = "https://api.learn.mit.edu/api/v1/courses/"
NOTE_PAGE_RE = re.compile(r"lecture[- ]?notes|lecture[- ]?summaries|lecture[- ]?handouts|class[- ]?notes|lecture[- ]?slides|readings", re.I)
SUBJECT_TOPICS = {"Computer Science": "Computer Science", "Physics": "Physics", "Biology": "Biology"}
# Only keep discovered courses from the matching MIT department (6 = EECS, 8 = Physics, 7 = Biology).
SUBJECT_DEPARTMENTS = {"Computer Science": ("6.",), "Physics": ("8.",), "Biology": ("7.",)}


class MitOcwCollector(Collector):
    def discover(self, subject: str, limit: int) -> list[dict]:
        found = []
        try:
            r = self.fetcher.client.get(LEARN_API, params={"platform": "ocw", "topic": SUBJECT_TOPICS[subject],
                                                           "limit": limit * 4}, timeout=30)
            r.raise_for_status()
            for it in r.json().get("results", []):
                url = it.get("url") or ""
                if "ocw.mit.edu/courses/" not in url:
                    continue
                runs = it.get("runs") or [{}]
                code = (it.get("readable_id") or "").split("+")[0]
                slug = url.rstrip("/").rsplit("/", 1)[-1]
                dept_ok = any(code.startswith(d) or slug.startswith(d.replace(".", "-")) for d in SUBJECT_DEPARTMENTS[subject])
                if self.config.get("department_only", True) and not dept_ok:
                    continue
                if len(found) >= limit:
                    break
                found.append({
                    "url": url if url.endswith("/") else url + "/",
                    "title": it.get("title", ""),
                    "code": (it.get("readable_id") or "").split("+")[0] or url.rstrip("/").rsplit("/", 1)[-1][:40],
                    "description": re.sub("<[^>]+>", "", it.get("description") or "")[:2000],
                    "term": f"{runs[0].get('semester') or ''} {runs[0].get('year') or ''}".strip(),
                })
            self.log(f"  MIT Learn API: discovered {len(found)} {subject} courses (MIT department {SUBJECT_DEPARTMENTS[subject][0]}x only)")
        except Exception as e:
            self.log(f"  course discovery unavailable for {subject} ({type(e).__name__}); using starter catalogue")
        return found

    def ensure_courses(self) -> list[Course]:
        limit = int(self.options.get("discover_limit", 15))
        if self.config.get("discover", True) and self.options.get("discover", True):
            for subj in self.subjects:
                for c in self.discover(subj, limit):
                    exists = self.db.scalar(select(Course).where(Course.source_id == self.source.id, Course.url == c["url"]))
                    if not exists:
                        exists = self.db.scalar(select(Course).where(Course.source_id == self.source.id, Course.code == c["code"]))
                    if not exists:
                        self.db.add(Course(source_id=self.source.id, code=c["code"], title=c["title"], subject=subj,
                                           university="MIT", url=c["url"], description=c["description"],
                                           term=c["term"], license=OCW_LICENSE))
            self.db.commit()
        q = select(Course).where(Course.source_id == self.source.id, Course.subject.in_(self.subjects))
        only = self.options.get("course_ids")
        if only:
            q = q.where(Course.id.in_(only))
        return list(self.db.scalars(q.order_by(Course.subject, Course.code)).all())

    def _soup(self, url: str) -> BeautifulSoup:
        return BeautifulSoup(self.fetcher.get(url).text, "lxml")

    def course_metadata(self, course: Course, soup: BeautifulSoup) -> None:
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True) and not course.title:
            course.title = h1.get_text(" ", strip=True)
        desc = soup.select_one("#course-description, .course-description, [data-testid=course-description]")
        if not desc:
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            text = meta.get("content", "") if meta else ""
        else:
            text = desc.get_text(" ", strip=True)
        if text and not course.description:
            course.description = text[:3000]
        instructors = [a.get_text(" ", strip=True) for a in soup.select(".course-info-instructor, a[href*='/search/?q=']")
                       if a.get_text(strip=True)]
        if instructors and not course.instructors:
            course.instructors = ", ".join(dict.fromkeys(instructors))[:480]
        lic = soup.find("a", href=re.compile(r"creativecommons\.org/licenses"))
        if lic:
            course.license = "Creative Commons " + lic["href"].rstrip("/").split("/licenses/")[-1].upper() + " (MIT OCW)"

    def candidates(self):
        max_per_course = int(self.options.get("max_docs_per_course") or self.config.get("max_docs_per_course", 12))
        for course in self.ensure_courses():
            if not course.url:
                continue
            self.log(f"MIT OCW · {course.code} {course.title}")
            try:
                home = self._soup(course.url)
            except Exception as e:
                self.log(f"  could not open course page: {e}")
                yield Candidate(url=course.url, title=f"{course.code} course page", subject=course.subject,
                                course_code=course.code, course_title=course.title, course_url=course.url,
                                university="MIT", license=course.license or OCW_LICENSE,
                                meta={"course_page": True, "error_hint": f"Could not open course page: {e}"}, fmt="html")
                continue
            self.course_metadata(course, home)
            self.db.commit()

            note_pages = []
            for a in home.find_all("a", href=True):
                href = urljoin(course.url, a["href"])
                if "/pages/" in href and (NOTE_PAGE_RE.search(href) or NOTE_PAGE_RE.search(a.get_text(" ", strip=True))):
                    if href not in note_pages:
                        note_pages.append(href)
            if not note_pages:
                note_pages = [urljoin(course.url, "pages/lecture-notes/")]
            # prefer lecture notes over readings
            note_pages.sort(key=lambda u: 0 if "lecture-notes" in u else 1)

            count = 0
            for page_url in note_pages[:3]:
                try:
                    page = self._soup(page_url)
                except Exception as e:
                    self.log(f"  no notes page at {page_url} ({e})")
                    continue
                main = page.select_one("main, #course-content-section, article") or page
                links = []
                for a in main.find_all("a", href=True):
                    href = urljoin(page_url, a["href"])
                    path = urlparse(href).path
                    if "ocw.mit.edu" not in href:
                        continue
                    if path.lower().endswith(".pdf") or "/resources/" in path:
                        label = a.get_text(" ", strip=True)
                        row = a.find_parent("tr")
                        if row:
                            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
                            label = " – ".join(x for x in cells if x and x.lower() not in ("pdf", "(pdf)"))[:200] or label
                        if href not in [x[0] for x in links]:
                            links.append((href, label))
                for href, label in links:
                    if count >= max_per_course:
                        break
                    file_url = href if href.lower().endswith(".pdf") else ""
                    resource_url = href
                    if not file_url:
                        try:
                            res = self._soup(href)
                            dl = res.find("a", href=re.compile(r"\.pdf($|\?)", re.I))
                            if not dl:
                                continue
                            file_url = urljoin(href, dl["href"])
                            h1 = res.find("h1")
                            if h1 and not label:
                                label = h1.get_text(" ", strip=True)
                        except Exception as e:
                            self.log(f"  resource failed {href}: {e}")
                            continue
                    count += 1
                    yield Candidate(
                        url=resource_url, file_url=file_url, title=label or f"{course.code} notes {count}",
                        subject=course.subject, fmt="pdf", course_code=course.code, course_title=course.title,
                        course_url=course.url, course_description=course.description, instructors=course.instructors,
                        term=course.term, university="MIT", author=course.instructors or "MIT OpenCourseWare",
                        license=course.license or OCW_LICENSE,
                    )
            if count == 0:
                self.log("  no downloadable lecture notes found")
