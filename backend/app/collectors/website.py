"""Crawl a public notes website (same host) collecting HTML note pages and linked PDFs."""

from __future__ import annotations

import re
from collections import deque
from urllib.parse import unquote, urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..seed import BIO_WORDS, CS_WORDS, PHYSICS_WORDS
from .base import Candidate, Collector

SKIP_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip", ".gz", ".tar", ".mp4", ".mp3", ".css", ".js", ".ico",
            ".xml", ".json", ".ppt", ".pptx", ".doc", ".docx", ".tex", ".bib", ".woff", ".woff2", ".ttf")


def guess_subject(text: str, allowed: list[str], default: str | None) -> str | None:
    t = text.lower()
    for pattern, subj in ((BIO_WORDS, "Biology"), (PHYSICS_WORDS, "Physics"), (CS_WORDS, "Computer Science")):
        if subj in allowed and re.search(pattern, t):
            return subj
    return default if default in allowed else None


class WebsiteCollector(Collector):
    def candidates(self):
        cfg = self.config
        start_urls = cfg.get("start") or [self.source.url]
        max_pages, max_depth = cfg.get("max_pages", 50), cfg.get("max_depth", 1)
        pdf_only = cfg.get("pdf_only", False)
        default = cfg.get("default_subject")
        host = urlparse(start_urls[0]).netloc
        queue = deque((u, 0) for u in start_urls)
        visited, yielded = set(), set()
        pages = 0
        while queue and pages < max_pages:
            url, depth = queue.popleft()
            url = urldefrag(url)[0]
            if url in visited:
                continue
            visited.add(url)
            try:
                r = self.fetcher.get(url)
            except Exception as e:
                self.log(f"  could not fetch {url}: {e}")
                if depth == 0:
                    raise
                continue
            pages += 1
            ctype = r.headers.get("content-type", "")
            if "pdf" in ctype:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            page_title = soup.title.get_text(strip=True) if soup.title else url
            path_parts = [p for p in urlparse(url).path.split("/") if p]
            course = path_parts[0] if cfg.get("course_from_path") and path_parts else "General"

            # the page itself as a note
            if not pdf_only and depth > 0 and url not in yielded:
                words = len(soup.get_text(" ", strip=True).split())
                subj = guess_subject(page_title + " " + url, self.subjects, default)
                if words >= 200 and subj:
                    yielded.add(url)
                    yield Candidate(url=url, title=page_title, subject=subj, fmt="html", data=r.content,
                                    course_code=course.upper() if cfg.get("course_from_path") else course,
                                    course_title=course.upper() if cfg.get("course_from_path") else "General notes",
                                    course_url=self.source.url, university=self.source.university,
                                    author=self.source.author, license=self.source.license)

            for a in soup.find_all("a", href=True):
                link = urldefrag(urljoin(url, a["href"]))[0]
                lp = urlparse(link)
                if lp.scheme not in ("http", "https"):
                    continue
                text = a.get_text(" ", strip=True) or unquote(lp.path.rsplit("/", 1)[-1])
                if lp.path.lower().endswith(".pdf"):
                    if link in yielded:
                        continue
                    subj = guess_subject(text + " " + link, self.subjects, default)
                    if not subj:
                        continue
                    yielded.add(link)
                    yield Candidate(url=link, file_url=link, title=text[:200], subject=subj, fmt="pdf",
                                    course_code=re.sub(r"\.pdf$", "", unquote(lp.path.rsplit("/", 1)[-1]))[:100],
                                    course_title=text[:200], course_url=url,
                                    university=self.source.university, author=self.source.author,
                                    license=self.source.license)
                elif lp.netloc == host and depth < max_depth and not lp.path.lower().endswith(SKIP_EXT):
                    queue.append((link, depth + 1))


class DirectPdfCollector(Collector):
    def candidates(self):
        for f in self.config.get("files", []):
            if f.get("subject") not in self.subjects:
                continue
            yield Candidate(url=f["url"], file_url=f["url"], title=f.get("title", ""), subject=f["subject"], fmt="pdf",
                            course_code=f.get("course", "General"), course_title=f.get("course_title", ""),
                            course_url=self.source.url, university=self.source.university,
                            author=self.source.author, license=self.source.license)
