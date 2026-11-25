"""The Git server in a container, through a container plugin's plans (the library's ContainedService, 1.94.0), on the
library's stand-ins alone (machines/servicestandins.py): no docker, no process, no socket. Its sign-in is your public
key, seeded before its first start; it runs on this PC alone until you Expose… it."""
from __future__ import annotations

import re

import pytest

from liminal_libs.instances import Refusal
from liminal_libs.machines.containedservice import UNREAD, Pace
from liminal_libs.machines.servicestandins import ServiceWorld, quick_pace

from plugin_platform_git import GitPlugin, recipe
from stand_ins import runner

KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKq3pS0e7n8bH2v5m1Yx9uQw4ZrT6cV0aB3dE5fG7hJ you@pc"
DIG = "sha256:" + "d" * 64


def pins(digest=DIG):
    return {s: {part: {**pin, "digest": digest} for part, pin in parts.items()} for s, parts in recipe.PINS.items()}


def world(tmp_path, pairs=None, digest=DIG):
    p = GitPlugin(runner=runner()[0], pace=quick_pace(), pins=pins(digest))
    w = ServiceWorld(p, pairs={recipe.KEY: KEY} if pairs is None else pairs, folder=tmp_path)
    return w, p


def test_its_shipped_pin_is_read_and_an_unread_one_is_refused(tmp_path):
    # read from Docker Hub on 2026-11-25 (its manifest list alone); an unread pin is still refused
    assert all(re.fullmatch(r"sha256:[0-9a-f]{64}", pin["digest"]) and pin["digest"] != UNREAD and pin["size"] > 0
               for parts in recipe.PINS.values() for pin in parts.values())
    w, p = world(tmp_path, digest=UNREAD)
    w.grant()
    with pytest.raises(Refusal, match="not pinned by digest yet"):
        w.ask("service_install", w.HOST, w.TARGET, "server", "no")


def test_it_is_never_installed_open_your_key_is_needed_first(tmp_path):
    w, p = world(tmp_path, pairs={})
    w.grant()
    with pytest.raises(Refusal, match="set GIT_SERVER_KEY"):
        w.ask("service_install", w.HOST, w.TARGET, "server", "no")
    w.login.env[recipe.KEY] = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXk\n-----END OPENSSH PRIVATE KEY-----"
    with pytest.raises(Refusal, match="holds a private key"):
        w.ask("service_install", w.HOST, w.TARGET, "server", "no")
    w.login.env[recipe.KEY] = "my password"
    with pytest.raises(Refusal, match="public key lines"):
        w.ask("service_install", w.HOST, w.TARGET, "server", "no")


def test_it_is_installed_on_this_pc_alone_first(tmp_path):
    w, p = world(tmp_path)
    w.grant()
    with pytest.raises(Refusal, match="this PC alone first"):
        w.ask("service_install", w.HOST, w.TARGET, "server", "yes")
    form = next(f for f in p.status()["forms"] if f["id"] == "install")
    assert [c["value"] for c in form["fields"][3]["choices"]] == ["no"]


def test_its_paths_are_the_ones_its_image_says():
    # its amd64 config blob, read 2026-11-25: SSH_AUTHORIZED_KEYS_FILE, GIT_REPOSITORIES_PATH, GIT_HOME
    part = recipe.spec("linux", "server", {}, KEY, pins()).parts[0]
    assert {v.name: v.path for v in part.volumes} == {"repos": "/srv/git", "keys": "/home/git/.ssh",
                                                      "commands": "/home/git/git-shell-commands"}
    assert [p.container for p in part.ports] == [22] and part.command == ()  # its own entrypoint and sshd run
    keys = next(s for s in part.seeds if s.path == "authorized_keys")
    assert keys.mode == 0o644 and next(v for v in part.volumes if v.name == "keys").owner is None


def test_its_install_seeds_your_key_restricted_and_its_two_commands(tmp_path):
    w, p = world(tmp_path)
    end = w.install("server", "no")
    assert end["ok"], end
    keys = w.fake.volumes["liminal-git-server-keys"]["files"]
    assert keys["authorized_keys"].decode() == f"restrict {KEY}\n"
    commands = w.fake.volumes["liminal-git-server-commands"]["files"]
    assert set(commands) == {"new", "list", "help"} and b"git init --bare" in commands["new"]
    [made] = w.fake.argv_of("create")
    said = " ".join(made)
    assert "-p 127.0.0.1:2222:22/tcp" in said and "PASSWORD" not in said  # the git user is given no password
    assert recipe.spec("linux", "server", {}, KEY, pins()).parts[0].env == {}
    assert any("ssh -p 2222 git@127.0.0.1 new" in line for line in end["lines"])
    assert p.placement("server")["state"] == "installed" and p.present()


def test_expose_opens_it_while_your_key_is_set(tmp_path):
    w, p = world(tmp_path)
    assert w.install("server", "no")["ok"]
    del w.login.env[recipe.KEY]
    with pytest.raises(Refusal, match="not opened to your network yet"):
        w.ask("service_change", "expose", "server", "on")
    w.login.env[recipe.KEY] = KEY
    assert w.through(w.ask("service_change", "expose", "server", "on"))["ok"]
    assert "-p 2222:22/tcp" in " ".join(w.fake.argv_of("create")[-1]) and p.placement("server")["lan"] is True


def test_its_changes_are_its_pages_alone(tmp_path):
    w, p = world(tmp_path)
    w.grant()
    with pytest.raises(Exception, match="page"):
        w.app.ask(p.name, "service_install", w.HOST, w.TARGET, "server", "no")


def test_on_windows_containers_it_has_no_image():
    with pytest.raises(Refusal, match="no windows image"):
        recipe.spec("windows", "server", {}, KEY, pins())


def test_the_seeded_commands_take_a_safe_name_alone():
    """`new`'s name check, as its shell reads it: letters, digits, '.', '_' and '-', never starting with '.'."""
    assert "''|.*|*[!A-Za-z0-9._-]*)" in recipe.NEW and 'repo="/srv/git/$name.git"' in recipe.NEW
