"""Git for Liminal, one of the platform's Source Control plugins (Monday list item 35; the user, 2026-11-22: "another
class of plugins for platform, classified source control"; 2026-11-23: "A Git plugin of its own", as Subversion's and
Mercurial's are: Git's version, the repositories on this PC and a plain Git server). Its SECTION is "scm": a platform
that draws that section (0.39.0) shows it under Source Control plugins, an older one under Machine plugins.

What it reads, when the platform asks and never on its own:
- Git's version (`git --version`, run without a window, outside any repository: tool.py);
- the repositories under the folders you name on its page (folders.py: never across a whole disk), each read from its
  own files alone (repos.py): its kind, branch, remotes (without a sign-in in their addresses) and when it changed.
  What was read is kept READ_S; Read again looks now.

What it changes, from its page alone (PAGE_ONLY_HOOKS, and checked again inside each): the folders it looks under
(kept through the login as GIT_FOLDERS); and its Git server, installed, started, stopped, updated and removed only as a
container, through the container plugin you pick, in that plugin's plans you approve (the library's ContainedService):
Git over SSH by your public key alone (GIT_SERVER_KEY, seeded before its first start), on this PC alone until you
Expose… it. Nothing else is written, and no repository is touched."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from liminal_libs.apps import asking
from liminal_libs.instances import Refusal
from liminal_libs.machines.containedservice import ContainedService, Pace
from liminal_libs.sources.keys import KeyVar

from . import apis as cards
from . import folders as F
from . import recipe, repos
from .tool import Runner, ToolError, version_of

__version__ = "0.1.0"
READ_S = 30.0
ROWS = 200
FOLDERS = "GIT_FOLDERS"
KEYS = (KeyVar(recipe.KEY, label="Your public key (the Git server's sign-in)", secret=False,
               hint=("optional: the line of your id_ed25519.pub (ssh-ed25519 AAAA… you@host), seeded as the Git server's "
                     "one sign-in before its first start; a public key is no secret, and a private one is refused")),)


def local(seconds: float) -> str:
    if not seconds:
        return "–"
    try:
        return datetime.fromtimestamp(seconds, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return "–"


@dataclass(frozen=True)
class Reading:
    at: float
    when: float
    folders: tuple[str, ...]
    path: str = ""
    version: str = ""
    trouble: str = ""
    found: tuple = field(default=())
    notes: tuple[str, ...] = ()


class GitPlugin(ContainedService):
    """Git here: its version, the repositories under your folders, and a Git server in a container."""

    name = "git"
    title = "Git"
    about = ("Git on this machine: its version and the repositories under the folders you name, each read from its own "
             "files; a plain Git server (over SSH, by your key) run in a container through the plugin you pick")
    api = "2.2"
    apis = cards.APIS
    order = 780  # the Source Control plugins: Git 780, GitHub 781, GitLab 782, Subversion 783, Mercurial 784
    ICON = "git"
    SECTION = "scm"
    SERVICE = "server"
    LAN_FIRST = False  # a seeded sign-in, this PC alone first (the user, 2026-11-25)
    DEFAULT_MEMORY_MB = recipe.MEMORY_MB
    HOOKS = (*ContainedService.HOOKS, "refresh", "add_folder", "remove_folder")
    READ_HOOKS = ("refresh",)
    PAGE_ONLY_HOOKS = ("add_folder", "remove_folder")
    INTERNAL_NOTES = (
        "Git is run for its version alone (git --version), without a window and outside any repository; a repository is "
        "read from its own files, so its configuration never makes git run a program.",
        f"Repositories are looked for under the folders you name alone ({FOLDERS}, through the login): never across a "
        f"whole disk, {F.MAX_DEPTH} folders down at most, no link followed.",
        "Its folders and its Git server's changes are its page's alone (PAGE_ONLY_HOOKS); the server runs only as a "
        "container, in a container plugin's plans you approve, by your public key alone.",
    )
    keys = KEYS

    def __init__(self, runner: Runner | None = None, pace: Pace | None = None, pins=None, clock=None, wall=None):
        ContainedService.__init__(self, pace)
        self._runner = runner or Runner()
        self._pins = pins
        self._clock = clock or time.monotonic
        self._wall = wall or time.time
        self._lock = threading.Lock()
        self._reading: Reading | None = None

    @property
    def KEEPS(self):  # noqa: N802 - read as a declared word
        return (*ContainedService.KEEPS.fget(self), (FOLDERS, "the folders its repositories are looked for under"))

    # -- reading -------------------------------------------------------------------------------------------------------
    def _folders(self) -> F.Folders:
        return F.Folders(FOLDERS, lambda: self.login)

    def _read(self, fresh: bool = False) -> Reading:
        folders = tuple(self._folders().all())
        with self._lock:
            kept = self._reading
        if kept is not None and not fresh and kept.folders == folders and self._clock() - kept.at < READ_S:
            return kept
        path = self._runner.find("git")
        version, trouble = "", ""
        if path:
            try:
                ran = self._runner.run("git", "--version")
                version = version_of(ran.out) if ran.code == 0 else ""
                trouble = "" if version else f"git --version said nothing of a version ({(ran.err or ran.out)[:120]})"
            except ToolError as e:
                trouble = str(e)
        look = F.look(list(folders), repos.kind_of)
        found = tuple(repos.read(p, k) for p, k in look.found)
        r = Reading(self._clock(), self._wall(), folders, path, version, trouble, found, tuple(look.notes))
        with self._lock:
            self._reading = r
        return r

    def _forget(self) -> None:
        with self._lock:
            self._reading = None

    def _key(self) -> str:
        try:
            return str((self.login.variables([recipe.KEY]) or {}).get(recipe.KEY) or "") if self.login else ""
        except Exception:  # noqa: BLE001 - a login that cannot be asked: none set
            return ""

    # -- its server (ContainedService) ---------------------------------------------------------------------------------
    def spec_for(self, system, name, options):
        """The Git server's recipe (recipe.py): Git over SSH, its sign-in your public key, seeded."""
        return recipe.spec(system, name, options, "" if options.get("fit") else self._key(), self._pins)

    def lan_ready(self, hosted):
        """Its sign-in is a key alone (no password is taken): opened to your network while your key is set."""
        try:
            recipe.authorized_keys(self._key())
        except Refusal as e:
            return False, str(e)
        return True, ""

    def after(self, action, hosted, line):
        """After its install: how a repository is made and cloned."""
        if action != "install":
            return []
        at = self.address(hosted) or f"127.0.0.1:{recipe.SSH_PORT}"
        port = at.rsplit(":", 1)[-1]
        return [f"make a repository: ssh -p {port} git@127.0.0.1 new <name>; clone it: git clone "
                f"ssh://git@127.0.0.1:{port}/srv/git/<name>.git"]

    def detach(self) -> None:
        self._forget()
        super().detach()

    # -- the hooks -------------------------------------------------------------------------------------------------------
    def present(self) -> bool:
        """Whether Git is on PATH here, or its server is placed in a container."""
        return self.service_present() or bool(self._runner.find("git"))

    def refresh(self) -> dict:
        """Git and the folders looked at again now."""
        r = self._read(fresh=True)
        return {"said": self._summary(r), "ok": True, "lines": list(r.notes) or [f"{len(r.found)} repositories"]}

    def _page(self, hook: str) -> None:
        who = asking.asker()
        if who != asking.PAGE:
            raise Refusal(f"git's {hook} is yours, from its page alone: {who or 'no one'} asked it")

    def add_folder(self, path) -> dict:
        """A folder its repositories are looked for under, added from its page alone (kept through the login)."""
        self._page("add_folder")
        added, where = self._folders().add(path)
        self._forget()
        return {"said": f"{added} is looked under now", "ok": True, "lines": [f"kept in {where}"]}

    def remove_folder(self, path) -> dict:
        """A folder taken off its list, from its page alone: nothing on the disk is touched."""
        self._page("remove_folder")
        gone, where = self._folders().remove(path)
        self._forget()
        return {"said": f"{gone} is no longer looked under (nothing on the disk was touched)", "ok": True,
                "lines": [f"kept in {where}"]}

    def api_facts(self) -> dict:
        """What it learned while it ran, asking nothing."""
        with self._lock:
            r = self._reading
        if r is None:
            return {}
        return {cards.CLI: {"Git": f"{r.version} at {r.path}" if r.version else (r.trouble or "not on PATH here"),
                            "Read": local(r.when)},
                cards.FILES: {"Folders": str(len(r.folders)), "Repositories": str(len(r.found))}}

    # -- the page --------------------------------------------------------------------------------------------------------
    @staticmethod
    def _summary(r: Reading) -> str:
        git = f"Git {r.version}" if r.version else ("Git is not on PATH here" if not r.path else "Git (its version not read)")
        if not r.folders:
            return f"{git} · no folder named to look for repositories under"
        return f"{git} · {len(r.found)} repositories under {len(r.folders)} folders"

    def status(self) -> dict:
        """Git's version, the folders and their repositories, and its server's containers."""
        r = self._read()
        out: dict = {"present": bool(r.path) or self.service_present(), "summary": self._summary(r),
                     "valid": self.service_valid() or bool(r.path), "why": "",
                     "git": r.version or r.trouble or "not on PATH here", "folders": len(r.folders),
                     "repositories": len(r.found), "readAt": f"{local(r.when)} (kept {READ_S:g} s; Read again looks now)"}
        if r.trouble:
            out["note"] = r.trouble
        out["tables"] = [self._folders_table(r), self._repos_table(r)]
        out["forms"] = self._forms(r)
        out["actions"] = [{"hook": "refresh", "args": [], "title": "Read again", "note": "looks at Git and the folders now"},
                          {"form": "add_folder", "title": "Add a folder…"}]
        if self.app is not None:
            svc = self.service_status()
            out["tables"] += svc.get("tables") or []
            out["forms"] += svc.get("forms") or []
        return out

    @staticmethod
    def _folders_table(r: Reading) -> dict:
        rows = [[f, {"form": "remove_folder", "title": "Remove…", "values": {"path": f}}] for f in r.folders]
        return {"title": "Folders looked under", "columns": [{"title": "Folder"}, {"title": "Remove"}], "rows": rows,
                "empty": "No folder yet: Add a folder… names one (repositories are never looked for across a disk).",
                "note": f"{F.MAX_DEPTH} folders down at most; no link followed; "
                        + ("; ".join(r.notes) if r.notes else "everything under them looked at")}

    @staticmethod
    def _repos_table(r: Reading) -> dict:
        rows = []
        for x in r.found[:ROWS]:
            branch = x.branch or (f"detached at {x.detached}" if x.detached else "–")
            remotes = ", ".join(f"{n}: {u}" for n, u in x.remotes) or "none"
            rows.append([{"text": os.path.basename(x.path) or x.path, "sub": x.path}, x.kind,
                         {"text": branch, "sub": x.why or None}, remotes, local(x.changed)])
        note = "read from each repository's files: git is never run in one"
        if len(r.found) > ROWS:
            note += f" · the first {ROWS} of {len(r.found):,}"
        return {"title": "Repositories", "columns": [{"title": "Repository"}, {"title": "Kind"}, {"title": "Branch"},
                                                     {"title": "Remotes"}, {"title": "Changed"}],
                "rows": rows, "note": note, "empty": "None found under the folders named."}

    @staticmethod
    def _forms(r: Reading) -> list[dict]:
        forms = [{"id": "add_folder", "hook": "add_folder", "title": "Add a folder to look under", "submit": "Review",
                  "fields": [{"name": "path", "label": "Folder", "type": "text", "value": "",
                              "placeholder": r"C:\Users\you\source"}],
                  "confirm": {"title": "Look for repositories under {path}?",
                              "words": "Its folders are looked at, four down at most, each time the page reads; nothing "
                                       "in them is changed.", "yes": "Add it"}}]
        if r.folders:
            forms.append({"id": "remove_folder", "hook": "remove_folder", "title": "Stop looking under a folder",
                          "fields": [{"name": "path", "label": "Folder", "type": "fixed"}],
                          "confirm": {"title": "Stop looking under {path}?", "words": "Nothing on the disk is touched.",
                                      "yes": "Remove it"}})
        return forms


MACHINE = GitPlugin()
