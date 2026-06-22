"""
ghostcorp/workspace.py — the product workspace: a real, git-backed directory the
AI company builds in.

On Sprint 0 the seed skeleton is copied into `workspace/product/` and committed.
From then on, the Engineer agent reads/writes real files here and the DevOps
agent commits each shipped feature, so the product has a genuine commit history
that the dashboard can show growing.

All file operations are confined to the workspace directory (no path escape).
The workspace is its own git repo (nested), and is gitignored by the parent repo.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_THIS = Path(__file__).resolve().parent
REPO_ROOT = _THIS.parent
SEED_DIR = _THIS / "seed"

WORKSPACE_DIR = Path(
    os.getenv("GHOSTCORP_WORKSPACE", str(REPO_ROOT / "workspace" / "product"))
).resolve()

_GIT_IDENTITY = [
    "-c", "user.email=founders@ghostcorp.ai",
    "-c", "user.name=GhostCorp Founders",
]

# Files/dirs never surfaced to agents or the file tree.
_IGNORE_DIRS = {".git", "__pycache__", ".pytest_cache"}
_IGNORE_SUFFIX = (".pyc", ".db", ".db-journal")


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(WORKSPACE_DIR), capture_output=True, text=True
    )


def exists() -> bool:
    return WORKSPACE_DIR.exists() and (WORKSPACE_DIR / "app.py").exists()


def init_workspace(force: bool = False) -> bool:
    """Materialize the seed skeleton into the workspace and make Sprint 0 commit.

    Returns True if a fresh workspace was created, False if one already existed
    and force was not set.
    """
    if WORKSPACE_DIR.exists():
        if not force:
            return False
        shutil.rmtree(WORKSPACE_DIR)

    WORKSPACE_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        SEED_DIR,
        WORKSPACE_DIR,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", ".pytest_cache"),
    )
    _git(["init", "-q"])
    _git(["add", "-A"])
    _git([*_GIT_IDENTITY, "commit", "-q", "-m", "Sprint 0: seed skeleton"])
    return True


def _safe(rel_path: str) -> Path:
    """Resolve a workspace-relative path, refusing anything that escapes it."""
    p = (WORKSPACE_DIR / rel_path).resolve()
    if not str(p).startswith(str(WORKSPACE_DIR)):
        raise ValueError(f"Path escapes workspace: {rel_path}")
    return p


def write_file(rel_path: str, content: str) -> str:
    p = _safe(rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return rel_path


def read_file(rel_path: str) -> str | None:
    p = _safe(rel_path)
    return p.read_text(encoding="utf-8") if p.exists() else None


def delete_file(rel_path: str) -> bool:
    p = _safe(rel_path)
    if p.exists() and p.is_file():
        p.unlink()
        return True
    return False


def list_files() -> list[str]:
    """All product source files, workspace-relative, sorted (excludes junk)."""
    out: list[str] = []
    for root, dirs, files in os.walk(WORKSPACE_DIR):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for f in files:
            if f.endswith(_IGNORE_SUFFIX) or f == ".gitignore":
                continue
            rel = os.path.relpath(os.path.join(root, f), WORKSPACE_DIR)
            out.append(rel.replace(os.sep, "/"))
    return sorted(out)


def commit(message: str) -> str | None:
    """Stage everything and commit. Returns the short SHA, or None if no change."""
    _git(["add", "-A"])
    status = _git(["status", "--porcelain"]).stdout.strip()
    if not status:
        return None
    _git([*_GIT_IDENTITY, "commit", "-q", "-m", message])
    return _git(["rev-parse", "--short", "HEAD"]).stdout.strip() or None


def working_diff() -> str:
    """Uncommitted changes (what the Engineer just wrote, pre-ship)."""
    return _git(["diff"]).stdout


def last_commit_diff(stat_only: bool = False) -> str:
    """Diff of the most recent commit (the last shipped feature)."""
    args = ["show", "--stat", "HEAD"] if stat_only else ["show", "HEAD"]
    return _git(args).stdout


def git_log(n: int = 25) -> list[dict]:
    """Recent commits as [{sha, message}] — the product's build history."""
    raw = _git(["log", f"-n{n}", "--pretty=%h\x1f%s"]).stdout.strip()
    log = []
    for line in raw.splitlines():
        if "\x1f" in line:
            sha, msg = line.split("\x1f", 1)
            log.append({"sha": sha, "message": msg})
    return log


def reset_workspace() -> None:
    """Wipe and re-seed (used by the API /reset)."""
    init_workspace(force=True)
