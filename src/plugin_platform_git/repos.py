"""A Git repository found under a folder you named, read from its own files alone: no git is run in it. Running git in a
repository reads that repository's configuration, which can name programs git then runs (core.fsmonitor, a clean
filter's process), so this plugin never does: its branch is read from HEAD, its remotes from its config, its last change
from its refs' times. A remote's address is said without what it may carry of a sign-in (user:token@ is taken out)."""
from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

MOST_READ = 64 * 1024  # a repository's small file read at most
WORKTREE, BARE, LINKED = "working tree", "bare", "linked working tree"


def _read(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return f.read(MOST_READ).decode("utf-8", "replace")
    except OSError:
        return ""


def git_dir_of(path: str) -> tuple[str, str]:
    """(the repository's git folder, its kind) for a folder that is a repository; ("", "") otherwise. A working tree
    has .git (a folder, or a file naming one: a linked working tree, a submodule); a bare repository is its own: HEAD,
    objects and refs beside its config saying bare."""
    dot = os.path.join(path, ".git")
    if os.path.isdir(dot) and os.path.isfile(os.path.join(dot, "HEAD")):
        return dot, WORKTREE
    if os.path.isfile(dot):
        found = re.match(r"gitdir:\s*(.+)", _read(dot).strip())
        if found:
            target = found.group(1).strip()
            target = target if os.path.isabs(target) else os.path.normpath(os.path.join(path, target))
            return target, LINKED
        return "", ""
    if (os.path.isfile(os.path.join(path, "HEAD")) and os.path.isdir(os.path.join(path, "objects"))
            and os.path.isdir(os.path.join(path, "refs"))
            and re.search(r"(?im)^\s*bare\s*=\s*true\s*$", _read(os.path.join(path, "config")))):
        return path, BARE
    return "", ""


def kind_of(path: str) -> str:
    return git_dir_of(path)[1]


def bare_address(url: str) -> str:
    """A remote's address without a user or password in it (https://user:token@host/x -> https://host/x); scp-like
    addresses (git@host:x) keep their user, which is no secret."""
    text = str(url or "").strip()
    if "://" not in text:
        return text
    try:
        parts = urlsplit(text)
    except ValueError:
        return "an address not read"
    if "@" not in parts.netloc:
        return text
    host = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))


@dataclass(frozen=True)
class Repo:
    """A repository as its files say it."""

    path: str
    kind: str
    branch: str = ""
    detached: str = ""
    remotes: tuple[tuple[str, str], ...] = field(default=())
    changed: float = 0.0
    why: str = ""


def _remotes(config: str) -> tuple[tuple[str, str], ...]:
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    try:
        parser.read_string(config)
    except configparser.Error:
        return ()
    out = []
    for section in parser.sections():
        found = re.fullmatch(r'remote\s+"(.+)"', section.strip())
        if found and parser.has_option(section, "url"):
            out.append((found.group(1), bare_address(parser.get(section, "url"))))
    return tuple(out[:8])


def read(path: str, kind: str = "") -> Repo:
    """A repository read from its files (Repo.why says what could not be read)."""
    gd, kind2 = git_dir_of(path)
    kind = kind or kind2
    if not gd:
        return Repo(path, kind or "?", why="its git folder is not there")
    head = _read(os.path.join(gd, "HEAD")).strip()
    branch = detached = ""
    found = re.match(r"ref:\s*refs/heads/(.+)", head)
    if found:
        branch = found.group(1).strip()
    elif re.fullmatch(r"[0-9a-f]{40,64}", head):
        detached = head[:12]
    common = gd
    if kind == LINKED:
        back = _read(os.path.join(gd, "commondir")).strip()
        if back:
            common = os.path.normpath(os.path.join(gd, back))
    remotes = _remotes(_read(os.path.join(common, "config")))
    changed = 0.0
    for p in (os.path.join(gd, "HEAD"), os.path.join(gd, "index"), os.path.join(common, "packed-refs"),
              os.path.join(common, "refs", "heads", branch) if branch else ""):
        try:
            changed = max(changed, os.path.getmtime(p)) if p else changed
        except OSError:
            pass
    why = "" if head else "its HEAD could not be read"
    return Repo(path, kind, branch, detached, remotes, changed, why)
