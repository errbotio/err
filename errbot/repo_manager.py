import json
import logging
import os
import re
import shutil
import tarfile
from collections import namedtuple
from datetime import datetime, timedelta
from os import path
from pathlib import Path
from typing import Dict, Generator, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from errbot.storage import StoreMixin
from errbot.storage.base import StoragePluginBase

from .utils import ON_WINDOWS, git_clone, git_pull

log = logging.getLogger(__name__)


def human_name_for_git_url(url: str) -> str:
    # try to humanize the last part of the git url as much as we can
    s = url.split(":")[-1].split("/")[-2:]
    if s[-1].endswith(".git"):
        s[-1] = s[-1][:-4]
    return str("/".join(s))


INSTALLED_REPOS = "installed_repos"

REPO_INDEXES_CHECK_INTERVAL = timedelta(hours=1)

REPO_INDEX = "repo_index"
LAST_UPDATE = "last_update"

RepoEntry = namedtuple(
    "RepoEntry", "entry_name, name, python, repo, path, avatar_url, documentation"
)
FIND_WORDS_RE = re.compile(r"(\w[\w']*\w|\w)")


class RepoException(Exception):
    pass


def makeEntry(repo_name: str, plugin_name: str, json_value: dict) -> RepoEntry:
    return RepoEntry(
        entry_name=repo_name,
        name=plugin_name,
        python=json_value["python"],
        repo=json_value["repo"],
        path=json_value["path"],
        avatar_url=json_value["avatar_url"],
        documentation=json_value["documentation"],
    )


def tokenizeJsonEntry(json_dict: dict) -> set:
    """
    Returns all the words in a repo entry.
    """
    search = " ".join((str(word) for word in json_dict.values()))
    return set(FIND_WORDS_RE.findall(search.lower()))


def which(program: str) -> Optional[str]:
    if ON_WINDOWS:
        program += ".exe"

    def is_exe(file_path):
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def check_dependencies(req_path: Path) -> Tuple[Optional[str], Sequence[str]]:
    """This methods returns a pair of (message, packages missing).
    Or None, [] if everything is OK.
    """
    log.debug("check dependencies of %s", req_path)
    # noinspection PyBroadException
    try:
        from importlib.metadata import distribution

        missing_pkg = []

        if not req_path.is_file():
            log.debug("%s has no requirements.txt file", req_path)
            return None, missing_pkg

        with req_path.open() as f:
            for line in f:
                stripped = line.strip()
                # skip empty lines.
                if not stripped:
                    continue

                # noinspection PyBroadException
                try:
                    distribution(stripped)
                except Exception:
                    missing_pkg.append(stripped)
        if missing_pkg:
            return (
                f"You need these dependencies for {req_path}: " + ",".join(missing_pkg),
                missing_pkg,
            )
        return None, missing_pkg
    except Exception:
        log.exception("Problem checking for dependencies.")
        return (
            "You need to have setuptools installed for the dependency check of the plugins",
            [],
        )


class BotRepoManager(StoreMixin):
    """
    Manages the repo list, git clones/updates or the repos.
    """

    def __init__(
        self,
        storage_plugin: StoragePluginBase,
        plugin_dir: str,
        plugin_indexes: Tuple[str, ...],
    ) -> None:
        """
        Make a repo manager.
        :param storage_plugin: where the manager store its state.
        :param plugin_dir: where on disk it will git clone the repos.
        :param plugin_indexes: a list of URL / path to get the json repo index.
        """
        super().__init__()
        self.plugin_indexes = plugin_indexes
        self.storage_plugin = storage_plugin
        self.plugin_dir = plugin_dir
        self.open_storage(storage_plugin, "repomgr")

    def shutdown(self) -> None:
        self.close_storage()

    def check_for_index_update(self) -> None:
        if REPO_INDEX not in self:
            log.info("No repo index, creating it.")
            self.index_update()
            return

        if (
            datetime.fromtimestamp(self[REPO_INDEX][LAST_UPDATE])
            < datetime.now() - REPO_INDEXES_CHECK_INTERVAL
        ):
            log.info("Index is too old, update it.")
            self.index_update()

    def index_update(self) -> None:
        index = {LAST_UPDATE: datetime.now().timestamp()}
        for source in reversed(self.plugin_indexes):
            try:
                if urlparse(source).scheme in ("http", "https"):
                    req = Request(source, headers={"User-Agent": "Errbot"})
                    with urlopen(url=req, timeout=10) as request:  # nosec
                        log.debug("Update from remote source %s...", source)
                        encoding = request.headers.get_content_charset()
                        content = request.read().decode(
                            encoding if encoding else "utf-8"
                        )
                else:
                    with open(source, encoding="utf-8", mode="r") as src_file:
                        log.debug("Update from local source %s...", source)
                        content = src_file.read()
                index.update(json.loads(content))
            except (HTTPError, URLError, IOError):
                log.exception(
                    "Could not update from source %s, keep the index as it is.", source
                )
                break
        else:
            # nothing failed so ok, we can store the index.
            self[REPO_INDEX] = index
            log.debug("Stored %d repo entries.", len(index) - 1)

    def get_repo_from_index(self, repo_name: str) -> List[RepoEntry]:
        """
        Retrieve the list of plugins for the repo_name from the index.

        :param repo_name: the name of the repo
        :return: a list of RepoEntry
        """
        plugins = self[REPO_INDEX].get(repo_name, None)
        if plugins is None:
            return None
        result = []
        for name, plugin in plugins.items():
            result.append(makeEntry(repo_name, name, plugin))
        return result

    def search_repos(self, query: str) -> Generator[RepoEntry, None, None]:
        """
        A simple search feature, keywords are AND and case insensitive on all the fields.

        :param query: a string query
        :return: an iterator of RepoEntry
        """
        # first see if we are up to date.
        self.check_for_index_update()
        if REPO_INDEX not in self:
            log.error("No index.")
            return
        query_work_set = set(FIND_WORDS_RE.findall(query.lower()))
        for repo_name, plugins in self[REPO_INDEX].items():
            if repo_name == LAST_UPDATE:
                continue
            for plugin_name, plugin in plugins.items():
                if query_work_set.intersection(tokenizeJsonEntry(plugin)):
                    yield makeEntry(repo_name, plugin_name, plugin)

    def get_installed_plugin_repos(self) -> Dict[str, str]:
        return self.get(INSTALLED_REPOS, {})

    def add_plugin_repo(self, name: str, url: str) -> None:
        with self.mutable(INSTALLED_REPOS, {}) as repos:
            repos[name] = url

    def set_plugin_repos(self, repos: Dict[str, str]) -> None:
        """Used externally."""
        self[INSTALLED_REPOS] = repos

    def get_all_repos_paths(self) -> List[str]:
        return [
            os.path.join(self.plugin_dir, d)
            for d in self.get(INSTALLED_REPOS, {}).keys()
        ]

    def install_repo(self, repo: str) -> str:
        """
        Install the repository from repo

        :param repo:
            The url, git url or path on disk of a repository. It can point to either a git repo or
             a .tar.gz of a plugin
        :returns:
            The path on disk where the repo has been installed on.
        :raises: :class:`~RepoException` if an error occured.
        """
        self.check_for_index_update()

        human_name = None
        # try to find if we have something with that name in our index
        if repo in self[REPO_INDEX]:
            human_name = repo
            repo_url = next(iter(self[REPO_INDEX][repo].values()))["repo"]
        elif not repo.endswith("tar.gz"):
            # This is a repo url, make up a plugin definition for it
            human_name = human_name_for_git_url(repo)
            repo_url = repo
        else:
            repo_url = repo

        # TODO: Update download path of plugin.
        if repo_url.endswith("tar.gz"):
            fo = urlopen(repo_url)  # nosec
            tar = tarfile.open(fileobj=fo, mode="r:gz")
            tar.extractall(path=self.plugin_dir)
            s = repo_url.split(":")[-1].split("/")[-1]
            human_name = s[: -len(".tar.gz")]
        else:
            human_name = human_name or human_name_for_git_url(repo_url)
            try:
                git_clone(repo_url, os.path.join(self.plugin_dir, human_name))
            except (
                Exception
            ) as exception:  # dulwich errors all base on exceptions.Exception
                raise RepoException(
                    f"Could not load this plugin: \n\n{repo_url}\n\n---\n\n{exception}"
                )

        self.add_plugin_repo(human_name, repo_url)
        return os.path.join(self.plugin_dir, human_name)

    def update_repos(self, repos) -> Generator[Tuple[str, int, str], None, None]:
        """
        This git pulls the specified repos on disk.
        Yields tuples like (name, success, reason)
        """
        # protects for update outside of what we know is installed
        names = set(self.get_installed_plugin_repos().keys()).intersection(set(repos))

        for d in (path.join(self.plugin_dir, name) for name in names):
            success = False
            try:
                git_pull(d)
                feedback = "Pulled remote"
                success = True
            except Exception as exception:
                feedback = f"Error pulling remote {exception}"
                pass

            dep_err, missing_pkgs = check_dependencies(Path(d) / "requirements.txt")
            if dep_err:
                feedback += dep_err + "\n"
            yield d, success, feedback

    def update_all_repos(self) -> Generator[Tuple[str, int, str], None, None]:
        return self.update_repos(self.get_installed_plugin_repos().keys())

    def uninstall_repo(self, name: str) -> None:
        repo_path = path.join(self.plugin_dir, name)
        # ignore errors because the DB can be desync'ed from the file tree.
        shutil.rmtree(repo_path, ignore_errors=True)
        repos = self.get_installed_plugin_repos()
        del repos[name]
        self.set_plugin_repos(repos)
