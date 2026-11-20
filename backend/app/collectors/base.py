from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import urlparse

import httpx

from ..config import Settings
from ..models import Source


@dataclass
class Candidate:
    url: str  # canonical public URL shown to users
    title: str
    subject: str
    file_url: str = ""  # direct download link (if different from url)
    local_file: str = ""  # already on disk (git mirror)
    repo_root: str = ""
    fmt: str = ""
    course_code: str = ""
    course_title: str = ""
    course_url: str = ""
    course_description: str = ""
    instructors: str = ""
    term: str = ""
    university: str = ""
    author: str = ""
    license: str = ""
    meta: dict = field(default_factory=dict)
    data: bytes | None = None  # pre-fetched content (website crawler)

    def to_meta(self) -> dict:
        d = asdict(self)
        d.pop("data", None)
        return d

    @classmethod
    def from_meta(cls, d: dict) -> "Candidate":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k != "data"})


class SkipDocument(Exception):
    pass


class Fetcher:
    """Polite HTTP client: identifies itself, honours robots.txt and rate-limits per host."""

    def __init__(self, settings: Settings, log: Callable[[str], None]):
        self.s = settings
        self.log = log
        self.client = httpx.Client(follow_redirects=True, timeout=60, headers={"User-Agent": settings.user_agent})
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last: dict[str, float] = {}

    def allowed(self, url: str) -> bool:
        if not self.s.respect_robots_txt:
            return True
        host = urlparse(url)
        base = f"{host.scheme}://{host.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.client.get(base + "/robots.txt", timeout=15)
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                    self._robots[base] = rp
                else:
                    self._robots[base] = None
            except httpx.HTTPError:
                self._robots[base] = None
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(self.s.user_agent, url)

    def get(self, url: str) -> httpx.Response:
        if not self.allowed(url):
            raise PermissionError(f"Blocked by robots.txt: {url}")
        host = urlparse(url).netloc
        wait = self.s.request_delay_seconds - (time.time() - self._last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self._last[host] = time.time()
        r = self.client.get(url)
        r.raise_for_status()
        if len(r.content) > self.s.max_download_mb * 1024 * 1024:
            raise SkipDocument(f"File larger than {self.s.max_download_mb} MB")
        return r


class Collector:
    def __init__(self, source: Source, settings: Settings, fetcher: Fetcher, log: Callable[[str], None],
                 subjects: list[str], options: dict, db=None):
        self.source = source
        self.settings = settings
        self.fetcher = fetcher
        self.log = log
        self.subjects = subjects or list(source.subjects or [])
        self.options = options or {}
        self.db = db
        self.config = source.config or {}

    @property
    def mirrors(self) -> Path:
        p = self.settings.data_path / "mirrors"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def candidates(self) -> Iterator[Candidate]:  # pragma: no cover - interface
        raise NotImplementedError
