"""git as a stand-in, and repositories as a few files. `FakeSpawn` is the runner's spawn (subprocess.run's shape): it
answers each argv it knows as git prints it and keeps every call with its keywords; `runner()` makes a Runner whose
`which` finds only the programs given. `worktree`, `bare` and `linked` write a repository's few files, as git lays them
out, under a test's temporary folder: nothing runs."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from plugin_platform_git.tool import Runner

GIT = r"C:\Program Files\Git\cmd\git.exe"


@dataclass
class Done:
    returncode: int
    stdout: str
    stderr: str = ""


class FakeSpawn:
    def __init__(self, answers=None):
        self.answers = {("--version",): Done(0, "git version 2.47.1.windows.1\n"), **(answers or {})}
        self.calls: list[tuple[list, dict]] = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), dict(kw)))
        got = self.answers.get(tuple(argv[1:]))
        if isinstance(got, BaseException):
            raise got
        return got or Done(1, "", f"unknown: {argv[1:]}")


def runner(found=("git",), spawn: FakeSpawn | None = None) -> tuple[Runner, FakeSpawn]:
    s = spawn or FakeSpawn()
    return Runner(which=lambda name: GIT if name in found else None, spawn=s), s


def worktree(root: Path, name: str, branch="main", remote="https://github.com/pcxmac-dev/liminal-libs.git") -> Path:
    p = root / name
    g = p / ".git"
    (g / "refs" / "heads").mkdir(parents=True)
    (g / "objects").mkdir()
    (g / "HEAD").write_text(f"ref: refs/heads/{branch}\n")
    (g / "refs" / "heads" / branch).write_text("1" * 40 + "\n")
    (g / "config").write_text("[core]\n\trepositoryformatversion = 0\n\tbare = false\n"
                              + (f'[remote "origin"]\n\turl = {remote}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
                                 if remote else ""))
    return p


def bare(root: Path, name: str) -> Path:
    p = root / name
    (p / "refs" / "heads").mkdir(parents=True)
    (p / "objects").mkdir()
    (p / "HEAD").write_text("ref: refs/heads/main\n")
    (p / "config").write_text("[core]\n\trepositoryformatversion = 0\n\tbare = true\n")
    return p


def linked(root: Path, main: Path, name: str, branch="feature") -> Path:
    gd = main / ".git" / "worktrees" / name
    gd.mkdir(parents=True)
    (gd / "HEAD").write_text(f"ref: refs/heads/{branch}\n")
    (gd / "commondir").write_text("../..\n")
    p = root / name
    p.mkdir()
    (p / ".git").write_text(f"gitdir: {os.fspath(gd)}\n")
    return p
