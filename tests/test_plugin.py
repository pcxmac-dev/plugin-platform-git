"""Git's version through the stand-in runner, the folders you name and the repositories found under them, read from
their files alone; its two changes asked from its page alone."""
from __future__ import annotations

import subprocess

import pytest

from liminal_libs.apps import asking
from liminal_libs.instances import Refusal
from liminal_libs.machines import standins

from plugin_platform_git import GitPlugin, folders as F, repos
from plugin_platform_git.tool import ToolError, version_of
from stand_ins import FakeSpawn, bare, linked, runner, worktree


def plugin(found=("git",), spawn=None, pairs=None):
    r, s = runner(found, spawn)
    p = GitPlugin(runner=r)
    p.login = standins.login(dict(pairs or {}))
    return p, s


def as_page(p, hook, *args):
    with asking.asking(asking.PAGE):
        return getattr(p, hook)(*args)


def test_its_version_is_git_run_once_without_a_window_outside_any_repository():
    p, s = plugin()
    st = p.status()
    assert st["git"] == "2.47.1.windows.1" and st["summary"].startswith("Git 2.47.1.windows.1")
    [(argv, kw)] = s.calls
    assert argv[1:] == ["--version"] and kw["stdin"] is subprocess.DEVNULL and kw["timeout"] <= 5
    assert kw["env"]["GIT_TERMINAL_PROMPT"] == "0" and kw["cwd"] and kw["check"] is False
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        assert kw["creationflags"] & 0x08000000
    p.status()
    assert len(s.calls) == 1  # kept READ_S
    p.refresh()
    assert len(s.calls) == 2


def test_no_git_here_is_said_and_nothing_runs():
    p, s = plugin(found=())
    st = p.status()
    assert s.calls == [] and "not on PATH" in st["summary"] and p.present() is False


def test_a_runner_that_cannot_start_or_waits_too_long_is_said_in_words():
    p, _ = plugin(spawn=FakeSpawn({("--version",): subprocess.TimeoutExpired("git", 5)}))
    assert "did not answer within" in p.status()["git"]
    with pytest.raises(ToolError, match="not on PATH"):
        runner(found=())[0].run("git", "--version")
    assert version_of("git version 2.39.5 (Apple Git-154)") == "2.39.5" and version_of("nothing") == ""


def test_folders_are_named_from_its_page_alone(tmp_path):
    p, _ = plugin()
    for who in ("a-harness", None):
        with asking.asking(who), pytest.raises(Refusal, match="from its page alone"):
            p.add_folder(str(tmp_path))
    assert p._folders().all() == []
    said = as_page(p, "add_folder", str(tmp_path))
    assert said["ok"] and p._folders().all() == [str(tmp_path)]
    with asking.asking("a-harness"), pytest.raises(Refusal, match="from its page alone"):
        p.remove_folder(str(tmp_path))
    as_page(p, "remove_folder", str(tmp_path))
    assert p._folders().all() == [] and tmp_path.is_dir()


def test_a_whole_disk_a_relative_path_or_a_folder_not_there_is_refused(tmp_path):
    p, _ = plugin()
    anchor = tmp_path.anchor
    for bad, words in ((anchor, "whole disk"), ("source", "no absolute path"), (str(tmp_path / "nope"), "not a folder"),
                       ("a\nb", "no line break")):
        with pytest.raises(Refusal, match=words):
            as_page(p, "add_folder", bad)
    as_page(p, "add_folder", str(tmp_path))
    with pytest.raises(Refusal, match="named already"):
        as_page(p, "add_folder", str(tmp_path))
    with pytest.raises(Refusal, match="not among"):
        as_page(p, "remove_folder", str(tmp_path / "other"))


def test_repositories_are_found_under_the_folders_and_read_from_their_files(tmp_path):
    w = worktree(tmp_path, "libs", remote="https://pcxmac:ghp_secret123@github.com/pcxmac-dev/liminal-libs.git")
    worktree(w, "vendored")  # inside a repository: never looked into
    b = bare(tmp_path / "srv", "app.git")
    linked(tmp_path, w, "libs-feature")
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    worktree(deep, "too-deep")
    (tmp_path / "node_modules").mkdir()
    worktree(tmp_path / "node_modules", "dep")
    p, s = plugin()
    as_page(p, "add_folder", str(tmp_path))
    st = p.status()
    rows = {r[0]["sub"]: r for r in st["tables"][1]["rows"]}
    assert set(rows) == {str(w), str(b), str(tmp_path / "libs-feature")}
    assert rows[str(w)][1] == "working tree" and rows[str(w)][2]["text"] == "main"
    assert rows[str(w)][3] == "origin: https://github.com/pcxmac-dev/liminal-libs.git"  # its token taken out
    assert "ghp_secret123" not in str(st)
    assert rows[str(b)][1] == "bare" and rows[str(tmp_path / "libs-feature")][2]["text"] == "feature"
    assert rows[str(tmp_path / "libs-feature")][3].startswith("origin: https://github.com/")  # its common config
    assert [argv[1:] for argv, _ in s.calls] == [["--version"]]  # git was never run in a repository


def test_a_detached_head_and_a_broken_gitfile_are_said(tmp_path):
    w = worktree(tmp_path, "w", remote="")
    (w / ".git" / "HEAD").write_text("a" * 40 + "\n")
    assert repos.read(str(w)).detached == "a" * 12 and repos.read(str(w)).remotes == ()
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / ".git").write_text("nonsense")
    assert repos.kind_of(str(tmp_path / "x")) == ""
    assert repos.bare_address("git@github.com:me/x.git") == "git@github.com:me/x.git"


def test_the_look_is_bounded(tmp_path, monkeypatch):
    for i in range(5):
        worktree(tmp_path, f"r{i}")
    monkeypatch.setattr(F, "MAX_FOUND", 3)
    look = F.look([str(tmp_path)], repos.kind_of)
    assert len(look.found) == 3 and "the first 3" in look.notes[0]
    monkeypatch.setattr(F, "MAX_DIRS", 0)
    assert "folders looked at" in F.look([str(tmp_path)], repos.kind_of).notes[0]


def test_a_link_is_not_followed(tmp_path):
    outside = tmp_path / "outside"
    worktree(outside, "elsewhere")
    top = tmp_path / "top"
    top.mkdir()
    try:
        (top / "link").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        try:  # Windows without the right to make a symbolic link: a junction, as mklink /J makes one (no process)
            import _winapi

            _winapi.CreateJunction(str(outside), str(top / "link"))
        except (ImportError, AttributeError, OSError):
            pytest.skip("this machine makes no link for a test")
    assert F.look([str(top)], repos.kind_of).found == []


def test_its_facts_ask_nothing():
    p, s = plugin()
    assert p.api_facts() == {}
    p.status()
    n = len(s.calls)
    facts = p.api_facts()
    assert len(s.calls) == n and facts["Git's command line"]["Git"].startswith("2.47.1.windows.1 at ")
