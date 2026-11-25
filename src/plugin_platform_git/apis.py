"""What the Git plugin attaches to (plugin API 2.2): Git's command line, which it asks for its version alone; a
repository's own files, which it reads a repository's branch and remotes from; and the Git server it runs in a
container, reached over SSH.

These cards were written on 2026-11-25 from Git's documentation as known to their writer; no page was fetched for this
build (its one network use was reading the image's digest). `LIMINAL_VENDOR_PAGES=1 pytest tests/test_apis.py` asks
every address on them once."""
from __future__ import annotations

from liminal_libs.sources.apis import Api, Area, Call, Link

VERIFIED = "2026-11-25"
CLI, FILES, SERVER = "Git's command line", "A Git repository's files", "The Git server (SSH and git-shell)"
_DOCS = "https://git-scm.com/docs/"

GIT_CLI = Api(
    name=CLI, maker="The Git project (open source, GPL-2.0)", kind="command",
    about=("git, the distributed version control system's program: its commands make, change, inspect and exchange "
           "repositories. The plugin runs it once per look, `git --version`, without a window, outside any repository, "
           "its prompts off: never in a repository, whose configuration can name programs git would run."),
    base="git on PATH",
    version="any Git 2: --version's line is read as it prints it (git version 2.47.1.windows.1)",
    auth="none: a local program, run as the signed-in user",
    limits="", costs="nothing: Git is free and open source",
    links=(Link("Git reference", _DOCS, "reference"), Link("Pro Git", "https://git-scm.com/book/en/v2", "guide"),
           Link("Downloads", "https://git-scm.com/downloads", "tool"),
           Link("git/git", "https://github.com/git/git", "source"),
           Link("Git release notes", "https://github.com/git/git/tree/master/Documentation/RelNotes", "changelog")),
    areas=(Area("Version", "the program's own version", _DOCS + "git#Documentation/git.txt---version",
                covered="Git's version on the page, and whether Git is here at all"),
           Area("Setup and configuration", "git config, git help"),
           Area("Getting and creating projects", "git init, git clone"),
           Area("Basic snapshotting", "git add, status, diff, commit, restore, reset, rm, mv"),
           Area("Branching and merging", "git branch, checkout, switch, merge, log, stash, tag, worktree"),
           Area("Sharing and updating", "git fetch, pull, push, remote, submodule"),
           Area("Inspection", "git show, log, diff, shortlog, describe"),
           Area("Administration", "git gc, fsck, reflog, filter-branch, maintenance")),
    calls=(Call("git --version", "prints Git's version", "Version", used="Git's version, once per look",
                docs=_DOCS + "git"),
           Call("git status", "a working tree's changes; reads the repository's configuration (core.fsmonitor can name "
                "a program it runs)", "Basic snapshotting", docs=_DOCS + "git-status"),
           Call("git init --bare", "a new bare repository", "Getting and creating projects", docs=_DOCS + "git-init",
                writes=True),
           Call("git clone", "a repository copied", "Getting and creating projects", docs=_DOCS + "git-clone",
                writes=True),
           Call("git fetch", "a remote's new commits fetched", "Sharing and updating", docs=_DOCS + "git-fetch",
                writes=True),
           Call("git push", "commits sent to a remote", "Sharing and updating", docs=_DOCS + "git-push", writes=True)),
    verified=VERIFIED)

GIT_FILES = Api(
    name=FILES, maker="The Git project", kind="file",
    about=("A repository's own files, as gitrepository-layout describes them: HEAD (the branch checked out, or a "
           "commit), config (its remotes among its settings), refs and packed-refs (its branches and tags), objects. "
           "The plugin reads HEAD, config, commondir and a .git file's gitdir line, and the times of HEAD, index and "
           "the branch's ref: nothing is written, and no program runs."),
    base="<repository>/.git, or a bare repository's own folder",
    version="the repository layout of Git 2 (repositoryformatversion 0 and 1)",
    auth="none: files the signed-in user can read",
    limits="each file read up to 64 KB", costs="",
    links=(Link("gitrepository-layout", _DOCS + "gitrepository-layout", "reference"),
           Link("git-config: its file's syntax", _DOCS + "git-config", "docs"),
           Link("git-worktree: linked working trees", _DOCS + "git-worktree", "guide")),
    areas=(Area("HEAD", "the branch checked out, or a detached commit", _DOCS + "gitrepository-layout",
                covered="the Branch column"),
           Area("config", "the repository's settings, its remotes among them", _DOCS + "git-config",
                covered="the Remotes column, each address without a user or password in it"),
           Area("gitfile and commondir", "a linked working tree's or a submodule's pointer to its git folder",
                _DOCS + "gitrepository-layout", covered="linked working trees found and read"),
           Area("refs and packed-refs", "the branches and tags", covered="the Changed column (their times)"),
           Area("objects", "the commits, trees and files themselves"),
           Area("hooks", "programs run at git's events (never run by the plugin)")),
    calls=(Call("read HEAD", "the branch or commit checked out", "HEAD", used="the Branch column"),
           Call("read config", "the remotes' names and addresses", "config", used="the Remotes column"),
           Call("read .git (a gitfile) and commondir", "where a linked working tree's git folder is", "gitfile and commondir",
                used="a linked working tree's branch and remotes"),
           Call("stat HEAD, index, refs/heads/<branch>, packed-refs", "when they last changed", "refs and packed-refs",
                used="the Changed column"),
           Call("read objects/", "a commit's contents", "objects")),
    verified=VERIFIED)

GIT_SERVER = Api(
    name=SERVER, maker="OpenSSH and the Git project, in rockstorm/git-server's image", kind="command",
    about=("The Git server the plugin runs in a container: OpenSSH taking the public keys seeded in authorized_keys, "
           "with git-shell as the git user's shell, so that a key runs git's own transport (git-upload-pack, "
           "git-receive-pack) and the commands in git-shell-commands, and nothing else. The plugin seeds its sign-in "
           "and two commands, new and list; its container is the container plugin's to run."),
    base="ssh://git@127.0.0.1:2222/srv/git/<name>.git (this PC alone until Expose…)",
    version="the pinned image, rockstorm/git-server 2.54 (Git 2.54)",
    auth="a public key you set (GIT_SERVER_KEY), seeded as authorized_keys with restrict; no password",
    limits="", costs="nothing",
    links=(Link("git-shell", _DOCS + "git-shell", "reference"),
           Link("Git on the server: setting up the server", "https://git-scm.com/book/en/v2/Git-on-the-Server-Setting-Up-the-Server",
                "guide"),
           Link("sshd: authorized_keys", "https://man.openbsd.org/sshd#AUTHORIZED_KEYS_FILE_FORMAT", "docs"),
           Link("rockstorm/git-server", "https://hub.docker.com/r/rockstorm/git-server", "tool"),
           Link("rockstorm101/git-server-docker", "https://github.com/rockstorm101/git-server-docker", "source")),
    areas=(Area("Sign-in", "the public keys in authorized_keys, each restricted", covered="seeded from GIT_SERVER_KEY"),
           Area("Git's transport", "clone, fetch and push over SSH", covered="said on the page: how to clone and push"),
           Area("git-shell commands", "the commands in ~/git-shell-commands", covered="new and list, seeded"),
           Area("Host keys", "the server's own keys, made at its first start")),
    calls=(Call("ssh git@<host> -p 2222 new <name>", "a bare repository made in /srv/git", "git-shell commands",
                used="said on the page: how to make a repository", writes=True),
           Call("ssh git@<host> -p 2222 list", "the repositories listed", "git-shell commands",
                used="said on the page"),
           Call("git clone ssh://git@<host>:2222/srv/git/<name>.git", "a repository cloned", "Git's transport"),
           Call("git push", "commits sent to it", "Git's transport", writes=True)),
    verified=VERIFIED)

APIS = (GIT_CLI, GIT_FILES, GIT_SERVER)
