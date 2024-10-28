import collections
import fnmatch
import importlib.metadata
import inspect
import logging
import os
import pathlib
import re
import sys
import time
from functools import wraps
from platform import system
from typing import List, Tuple, Union

from dulwich import porcelain

log = logging.getLogger(__name__)

ON_WINDOWS = system() == "Windows"

PLUGINS_SUBDIR = "plugins"


# noinspection PyPep8Naming
class deprecated:
    """deprecated decorator. emits a warning on a call on an old method and call the new method anyway"""

    def __init__(self, new=None):
        self.new = new

    def __call__(self, old):
        @wraps(old)
        def wrapper(*args, **kwds):
            frame = inspect.getframeinfo(inspect.currentframe().f_back)
            msg = f"{frame.filename}: {frame.lineno}: "
            if len(args):
                pref = (
                    type(args[0]).__name__ + "."
                )  # TODO might break for individual methods
            else:
                pref = ""
            msg += f"call to the deprecated {pref}{old.__name__}"
            if self.new is not None:
                if type(self.new) is property:
                    msg += (
                        f"... use the property {pref}{self.new.fget.__name__} instead"
                    )
                else:
                    msg += f"... use {pref}{self.new.__name__} instead"
            msg += "."
            logging.warning(msg)

            if self.new:
                if type(self.new) is property:
                    return self.new.fget(*args, **kwds)
                return self.new(*args, **kwds)
            return old(*args, **kwds)

        wrapper.__name__ = old.__name__
        wrapper.__doc__ = old.__doc__
        wrapper.__dict__.update(old.__dict__)
        return wrapper


def format_timedelta(timedelta) -> str:
    total_seconds = timedelta.seconds + (86400 * timedelta.days)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours == 0 and minutes == 0:
        return f"{seconds:d} seconds"
    elif not hours:
        return f"{minutes:d} minutes"
    elif not minutes:
        return f"{hours:d} hours"
    return f"{hours:d} hours and {minutes:d} minutes"


INVALID_VERSION_EXCEPTION = 'version %s in not in format "x.y.z" or "x.y.z-{beta,alpha,rc1,rc2...}" for example "1.2.2"'


def version2tuple(version: str) -> Tuple:
    vsplit = version.split("-")

    if len(vsplit) == 2:
        main, sub = vsplit
        if sub == "alpha":
            sub_int = -1
        elif sub == "beta":
            sub_int = 0
        elif sub.startswith("rc"):
            sub_int = int(sub[2:])
        else:
            raise ValueError(INVALID_VERSION_EXCEPTION % version)

    elif len(vsplit) == 1:
        main = vsplit[0]
        sub_int = sys.maxsize
    else:
        raise ValueError(INVALID_VERSION_EXCEPTION % version)

    response = [int(el) for el in main.split(".")]
    response.append(sub_int)

    if len(response) != 4:
        raise ValueError(INVALID_VERSION_EXCEPTION % version)

    return tuple(response)


REMOVE_EOL = re.compile(r"\n")
REINSERT_EOLS = re.compile(r"</p>|</li>|<br/>", re.I)
ZAP_TAGS = re.compile(r"<[^>]+>")


def rate_limited(min_interval: Union[float, int]):
    """
    decorator to rate limit a function.

    :param min_interval: minimum interval allowed between 2 consecutive calls.
    :return: the decorated function
    """

    def decorate(func):
        last_time_called = [0.0]

        def rate_limited_function(*args, **kargs):
            elapsed = time.time() - last_time_called[0]
            log.debug("Elapsed %f since last call", elapsed)
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                log.debug("Wait %f due to rate limiting...", left_to_wait)
                time.sleep(left_to_wait)
            ret = func(*args, **kargs)
            last_time_called[0] = time.time()
            return ret

        return rate_limited_function

    return decorate


def split_string_after(str_: str, n: int) -> str:
    """Yield chunks of length `n` from the given string

    :param n: length of the chunks.
    :param str_: the given string.
    """
    for start in range(0, max(len(str_), 1), n):
        yield str_[start : start + n]


def find_roots(path: str, file_sig: str = "*.plug") -> List:
    """Collects all the paths from path recursively that contains files of type `file_sig`.

    :param path:
         a base path to walk from
    :param file_sig:
         the file pattern to look for
    :return: a list of paths
    """
    roots = list()  # you can have several .plug per directory.
    for root, dirnames, filenames in os.walk(path, followlinks=True):
        for filename in fnmatch.filter(filenames, file_sig):
            dir_to_add = os.path.dirname(os.path.join(root, filename))
            relative = os.path.relpath(
                os.path.realpath(dir_to_add), os.path.realpath(path)
            )
            for subelement in relative.split(os.path.sep):
                # if one of the element is just a relative construct, it is ok to continue inspecting it.
                if subelement in (".", ".."):
                    continue
                # if it is an hidden directory or a python temp directory, just ignore it.
                if subelement.startswith(".") or subelement == "__pycache__":
                    log.debug("Ignore %s.", dir_to_add)
                    break
            else:
                roots.append(dir_to_add)
    return list(collections.OrderedDict.fromkeys(roots))


def collect_roots(base_paths: List, file_sig: str = "*.plug") -> List:
    """Collects all the paths from base_paths recursively that contains files of type `file_sig`.

    :param base_paths:
         a list of base paths to walk from
         elements can be a string or a list/tuple of strings

    :param file_sig:
         the file pattern to look for
    :return: a list of paths
    """
    result = list()
    for path_or_list in base_paths:
        if isinstance(path_or_list, (list, tuple)):
            result.extend(collect_roots(base_paths=path_or_list, file_sig=file_sig))
        elif path_or_list is not None:
            result.extend(find_roots(path_or_list, file_sig))
    return list(collections.OrderedDict.fromkeys(result))


def entry_point_plugins(group):
    paths = []

    eps = importlib.metadata.entry_points()
    try:
        entry_points = eps.select(group=group)
    except AttributeError:
        # workaround to support python 3.9 and older
        entry_points = eps.get(group, ())

    for entry_point in entry_points:
        module_name = entry_point.module
        file_name = module_name.replace(".", "/") + ".py"
        try:
            files = entry_point.dist.files
        except AttributeError:
            # workaround to support python 3.9 and older
            try:
                files = importlib.metadata.distribution(entry_point.name).files
            except importlib.metadata.PackageNotFoundError:
                # entrypoint is not a distribution, so let's skip looking for files
                continue

        for f in files:
            if file_name == str(f):
                parent = str(pathlib.Path(f).resolve().parent)
                paths.append(f"{parent}/{module_name}")
    return paths


def global_restart() -> None:
    """Restart the current process."""
    python = sys.executable
    os.execl(python, python, *sys.argv)


def git_clone(url: str, path: str) -> None:
    """
    Clones a repository from git url to path
    """
    if not os.path.exists(path):
        os.makedirs(path)

    repo = porcelain.clone(url, path)
    config = repo.get_config()
    config.set(("branch", "master"), "remote", "origin")
    config.set(("branch", "master"), "merge", "refs/heads/master")
    config.write_to_path()


def git_pull(repo_path: str) -> None:
    """
    Does a git pull on a repository
    """
    porcelain.pull(repo_path)


def git_tag_list(repo_path: str) -> List[str]:
    """
    Lists git tags on a cloned repo
    """
    porcelain.tag_list(repo_path)
