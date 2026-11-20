"""Collect notes from public GitHub repositories (Markdown, LaTeX, PDF, HTML)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

from ..seed import NO_LICENSE
from .base import Candidate, Collector


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} failed: {r.stderr.strip()[:500]}")


def _titleize(s: str) -> str:
    s = re.sub(r"[-_]+", " ", s).strip()
    return s[:1].upper() + s[1:] if s else s


class GitHubCollector(Collector):
    def sync_repo(self) -> Path:
        repo = self.config["repo"]
        branch = self.config.get("branch", "main")
        dest = self.mirrors / repo.replace("/", "__")
        url = f"https://github.com/{repo}.git"
        if not shutil.which("git"):
            raise RuntimeError("git is not installed – it is required for GitHub sources")
        sparse = self.config.get("sparse")
        if dest.exists() and (dest / ".git").exists():
            self.log(f"Updating mirror {repo}")
            try:
                _run(["git", "fetch", "--depth", "1", "origin", branch], dest)
                _run(["git", "reset", "--hard", "FETCH_HEAD"], dest)
            except RuntimeError as e:
                self.log(f"  update failed, using existing copy ({e})")
        else:
            self.log(f"Cloning {repo} ({'sparse' if sparse else 'full'}) …")
            if dest.exists():
                shutil.rmtree(dest)
            if sparse:
                _run(["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout", "-b", branch, url, str(dest)])
                _run(["git", "sparse-checkout", "set", "--no-cone", *sparse], dest)
                _run(["git", "checkout", branch], dest)
            else:
                _run(["git", "clone", "--depth", "1", "-b", branch, url, str(dest)])
        return dest

    def detect_license(self, root: Path) -> str:
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "license"):
            p = root / name
            if p.is_file():
                head = p.read_text("utf-8", "replace").strip().split("\n")[0].strip()
                return f"{head} (from repository {name})"
        return ""

    def candidates(self):
        root = self.sync_repo()
        repo = self.config["repo"]
        branch = self.config.get("branch", "main")
        lic = self.source.license
        detected = self.detect_license(root)
        if detected and (not lic or lic == NO_LICENSE):
            lic = detected
        seen = set()
        for item in self.config.get("items", []):
            for path in sorted(root.glob(item["glob"])):
                if not path.is_file() or path in seen:
                    continue
                rel = path.relative_to(root).as_posix()
                if any(re.search(x, rel) for x in item.get("exclude", [])):
                    continue
                subject = item.get("subject")
                for pattern, subj in item.get("subject_rules", []):
                    if re.search(pattern, rel, re.I):
                        subject = subj
                        break
                if not subject or subject not in self.subjects:
                    continue
                if item.get("tex_main_only"):
                    head = path.read_text("utf-8", "replace")
                    if "\\documentclass" not in head or re.search(r"\\documentclass(\[[^\]]*\])?\{(standalone|subfiles)\}", head):
                        continue
                seen.add(path)
                parts = rel.split("/")
                stem = path.stem
                vars_ = {
                    "path": quote(rel), "dir": quote("/".join(parts[:-1])), "stem": stem,
                    "parent": _titleize(path.parent.name), "seg1": parts[1] if len(parts) > 2 else parts[0],
                    "seg1_title": _titleize(parts[1] if len(parts) > 2 else parts[0]).title(),
                    "stem_course": re.sub(r"\s*Notes$", "", stem), "doc_title": "{doc_title}",
                }
                fmt = {"md": "md", "markdown": "md", "tex": "tex", "pdf": "pdf"}.get(path.suffix.lower().lstrip("."), "html")
                yield Candidate(
                    url=item.get("url", "https://github.com/" + repo + "/blob/" + branch + "/{path}").format(**vars_),
                    file_url=f"https://raw.githubusercontent.com/{repo}/{branch}/{quote(rel)}",
                    title=_titleize(stem) if fmt != "html" else "",
                    subject=subject,
                    local_file=str(path), repo_root=str(root), fmt=fmt,
                    course_code=item.get("course", "{parent}").format(**vars_),
                    course_title=item.get("course_title", "{parent}").format(**vars_),
                    course_url=self.source.url,
                    university=self.source.university, author=self.source.author, license=lic,
                    meta={"repo": repo, "path": rel},
                )
