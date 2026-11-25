# plugin-platform-git

Git for Liminal, one of the platform's Source Control plugins (Monday list item 35; the user, 2026-11-23: "A Git plugin
of its own": Git's version, the repositories on this PC and a plain Git server). `SECTION` "scm", icon `git`.

## What it does

- **Git's version**: `git --version`, run once per look without a window (CREATE_NO_WINDOW), its standard input
  closed, outside any repository (the system's temporary folder), its prompts off, five seconds at most.
- **The folders you name** on its page (Add a folder…, Remove…), kept through the login as `GIT_FOLDERS`: an
  absolute path to a folder that is there, never a drive's or the file system's root, 16 at most. It looks four
  folders down at most, follows no link (symbolic link, junction), steps over `node_modules`, `.venv` and the like,
  and never goes into what it found. Nothing is ever looked for across a whole disk.
- **Each repository read from its own files** (`repos.py`): working trees, linked working trees and bare
  repositories; the branch from HEAD (or the detached commit), the remotes from config (each address without a
  user or password in it), when it last changed from its refs' times. Git is never run in a repository: its
  configuration can name programs git would run (core.fsmonitor, a clean filter's process).
- **A plain Git server in a container** (`recipe.py`, the library's ContainedService): Git over SSH
  (rockstorm/git-server 2.54: OpenSSH with git-shell), installed, started, stopped, updated and removed only as a
  container through the container plugin you pick, each change a plan you approve on the page. Its sign-in is your
  public key (`GIT_SERVER_KEY`, through the login; a private key is refused), seeded into a new volume as
  `authorized_keys`, each line `restrict`ed; passwords are not taken. Two commands are seeded for git-shell:
  `ssh -p 2222 git@127.0.0.1 new <name>` makes a bare repository, `list` lists them. On this PC alone
  (127.0.0.1:2222) until you Expose… it.

## Its pin

`docker.io/rockstorm/git-server:2.54` at `sha256:302c9346…23bd4b`, read from Docker Hub on 2026-11-25 (its manifest list
alone; no image pulled), 12.9 MB for amd64. What the image does with `/srv/git`, `/home/git/.ssh`,
`git-shell-commands` and `SSH_AUTH_METHODS` is its README's word, not read again for this release: check it before
your first Install…. An unread pin (`UNREAD`) is refused before any plan.

## Tests

Stand-ins alone: no git, docker or network is run or reached (`tests/conftest.py` refuses every process and
connection while a test runs). Run them with the library on the path:

    PYTHONPATH="src;<liminal-libs>/src" python -m pytest -q -p no:cacheprovider

`LIMINAL_VENDOR_PAGES=1` lets `tests/test_apis.py` ask every address on its API cards once (the only test that reaches
the network). Each gate was taken out once and a test seen to fail.
