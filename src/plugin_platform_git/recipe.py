"""A plain Git server's recipe for a container (0.1.0; Monday list item 35, with the user's answers of 2026-11-23 and
2026-11-25: every server in a container through the container plugin you pick, a seeded sign-in, this PC alone first,
then Expose…, images pinned by digest).

One part, `server`: Git over SSH (rockstorm/git-server: Alpine's OpenSSH with git-shell as the git user's shell, so a
key signs in for git's own commands and nothing else). Its sign-in is seeded before the first start, into the new
`keys` volume alone: an authorized_keys holding the one public key you set (GIT_SERVER_KEY, through the login: a public
key is no secret, and a private key is refused), each line `restrict`ed (no shell, no forwarding, no terminal),
root's and readable by all (0644: sshd reads it as the git user, whatever that user's uid); the git user is given no
password (the image sets one only from GIT_PASSWORD, which this recipe never sets). Two commands are seeded into
git-shell's own folder, so that a
repository is made over the same sign-in: `ssh -p 2222 git@127.0.0.1 new <name>` makes /srv/git/<name>.git (bare),
`list` lists them. Repositories live in the `repos` volume. Installed on this PC alone (127.0.0.1:2222); Expose… opens
it to your network.

The pin: read from Docker Hub on 2026-11-25 (its manifest list, then its amd64 config blob; no layer, no image
pulled). The config says: Entrypoint /docker-entrypoint.sh, Cmd /usr/sbin/sshd -D, no User (it starts as root), port
22/tcp, no declared volume, and SSH_AUTHORIZED_KEYS_FILE=/home/git/.ssh/authorized_keys, GIT_REPOSITORIES_PATH=/srv/git,
GIT_HOME=/home/git, GIT_USER=git: the paths this recipe uses. It does not say the git user's uid (1000, the repos
volume's owner here, is Alpine's first user's: check it at your first Install…, or pushes to /srv/git are refused);
SSH_AUTH_METHODS, which an earlier draft set, is none of the image's variables and is not set."""
from __future__ import annotations

import re
from collections.abc import Mapping

from liminal_libs.instances import Refusal
from liminal_libs.machines.containers import ServiceSpec

OWNER = "git"
KEY = "GIT_SERVER_KEY"  # the public key you sign in with: a pair through the login
SSH_PORT = 2222  # on this machine; the container's own is 22
MEMORY_MB = 256
UID = 1000  # the image's git user
HUB = "https://hub.docker.com/r/"
PINS = {
    "linux": {
        "server": dict(ref="docker.io/rockstorm/git-server:2.54",
                       digest="sha256:302c9346c306ea12b84dcebe79b7d653a07a27aac4c15e1fc8eea4537423bd4b",
                       size=12890408, system="linux",
                       platforms=["linux/amd64", "linux/arm64"], version="2.54", licence="MIT (the image); GPL-2.0 (Git)",
                       page=HUB + "rockstorm/git-server", tar=True),
    },
}
KEY_LINE = re.compile(r"^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)|sk-ssh-ed25519@openssh\.com|"
                      r"sk-ecdsa-sha2-nistp256@openssh\.com) [A-Za-z0-9+/]{40,}={0,3}( [^\r\n]{0,200})?$")
NEW = """#!/bin/sh
# seeded by Liminal (plugin-platform-git 0.1.0): `new <name>` makes the bare repository /srv/git/<name>.git
set -eu
name="${1:-}"
name="${name%.git}"
case "$name" in
  ''|.*|*[!A-Za-z0-9._-]*) echo "new <name>: letters, digits, '.', '_' and '-', not starting with '.'" >&2; exit 2 ;;
esac
repo="/srv/git/$name.git"
if [ -e "$repo" ]; then echo "$repo is there already" >&2; exit 1; fi
git init --bare --quiet "$repo"
echo "made $repo: git clone ssh://git@<this machine>:2222$repo"
"""
LIST = """#!/bin/sh
# seeded by Liminal (plugin-platform-git 0.1.0): the repositories in /srv/git
for repo in /srv/git/*.git; do [ -d "$repo" ] && echo "$repo"; done; exit 0
"""
HELP = """#!/bin/sh
# seeded by Liminal (plugin-platform-git 0.1.0)
echo "This Git server takes git's own commands, and: new <name>, list"
"""


def authorized_keys(text: str) -> str:
    """The authorized_keys seeded: each public key line `restrict`ed; Refusal for a private key or anything else."""
    lines = [x.strip() for x in str(text or "").replace("\r", "\n").split("\n") if x.strip()]
    if any("PRIVATE KEY" in x for x in lines):
        raise Refusal(f"{KEY} holds a private key: set the public one (its .pub file), and keep the private one to "
                      "yourself")
    if not lines:
        raise Refusal(f"set {KEY} to your public key (the line of your id_ed25519.pub) in its settings first: the Git "
                      "server's sign-in is seeded with it before its first start, so it never runs open")
    if len(lines) > 8 or not all(KEY_LINE.match(x) for x in lines):
        raise Refusal(f"{KEY} is one to eight public key lines (ssh-ed25519 AAAA… you@host), nothing else")
    return "".join(f"restrict {x}\n" for x in lines)


def spec(system: str, name: str, options: Mapping, key: str, pins: Mapping | None = None) -> ServiceSpec:
    """The Git server's spec for a system (Linux alone: the image is a Linux one). `key`: GIT_SERVER_KEY's lines ("" only
    for reading a fit, with no seed)."""
    pins = pins if pins is not None else PINS
    if system not in pins:
        raise Refusal(f"the Git server has no {system} image")
    fit = bool(options.get("fit"))
    seeds = [] if fit else [
        {"volume": "keys", "path": "authorized_keys", "text": authorized_keys(key), "mode": 0o644},
        {"volume": "commands", "path": "new", "text": NEW, "mode": 0o755},
        {"volume": "commands", "path": "list", "text": LIST, "mode": 0o755},
        {"volume": "commands", "path": "help", "text": HELP, "mode": 0o755}]
    ports = list(options.get("ports") or [])
    host = int(ports[0]) if ports else SSH_PORT
    server = {
        "name": "server", "image": dict(pins[system]["server"]),
        "ports": [{"name": "ssh", "container": 22, "host": host, "lan": bool(options.get("lan")),
                   "about": "Git over SSH, by key alone"}],
        "volumes": [{"name": "repos", "path": "/srv/git", "holds": "its repositories", "owner": UID},
                    {"name": "keys", "path": "/home/git/.ssh", "holds": "the public keys that sign in", "owner": None},
                    {"name": "commands", "path": "/home/git/git-shell-commands",
                     "holds": "the commands git-shell takes beside git's (new, list)", "owner": UID}],
        "seeds": seeds,
        "memory": (int(options.get("memory_mb") or 0) or MEMORY_MB) << 20,
        "health": {"port": "ssh", "path": "", "ready_s": 60}, "stop_s": 10}
    return ServiceSpec.of({"owner": OWNER, "name": name, "title": "Git server", "system": system, "parts": [server]})
