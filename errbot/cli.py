#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import argparse
import ast
import logging
import os
import sys
from os import W_OK, access, getcwd, path, sep
from pathlib import Path
from platform import system
from typing import Optional, Union
from collections.abc import Mapping

from errbot.bootstrap import CORE_BACKENDS
from errbot.logs import root_logger
from errbot.plugin_wizard import new_plugin_wizard
from errbot.utils import collect_roots, entry_point_plugins
from errbot.version import VERSION

log = logging.getLogger(__name__)


# noinspection PyUnusedLocal
def debug(sig, frame) -> None:
    """Interrupt running process, and provide a python prompt for
    interactive debugging."""
    d = {"_frame": frame}  # Allow access to frame object.
    d.update(frame.f_globals)  # Unless shadowed by global
    d.update(frame.f_locals)

    i = code.InteractiveConsole(d)
    message = "Signal received : entering python shell.\nTraceback:\n"
    message += "".join(traceback.format_stack(frame))
    i.interact(message)


ON_WINDOWS = system() == "Windows"

if not ON_WINDOWS:
    import code
    import signal
    import traceback

    from daemonize import Daemonize

    signal.signal(signal.SIGUSR1, debug)  # Register handler for debugging


def get_config(config_path: str):
    config_fullpath = config_path
    if not path.exists(config_fullpath):
        log.error(f"I cannot find the config file {config_path}.")
        log.error("You can change this path with the -c parameter see --help")
        log.info(
            f'You can use the template {os.path.realpath(os.path.join(__file__, os.pardir, "config-template.py"))}'
            f" as a base and copy it to {config_path}."
        )
        log.info("You can then customize it.")
        exit(-1)

    try:
        config = __import__(path.splitext(path.basename(config_fullpath))[0])
        log.info("Config check passed...")
        return config
    except Exception:
        log.exception(
            f"I could not import your config from {config_fullpath}, please check the error below..."
        )
        exit(-1)


def _read_dict() -> Mapping:

    new_dict = ast.literal_eval(sys.stdin.read())
    if not isinstance(new_dict, Mapping):
        raise ValueError(
            f"A dictionary written in python is needed from stdin. "
            f"Type={type(new_dict)}, Value = {repr(new_dict)}."
        )
    return new_dict


def main() -> None:
    execution_dir = getcwd()

    # By default insert the execution path (useful to be able to execute Errbot from
    # the source tree directly without installing it.
    sys.path.insert(0, execution_dir)

    parser = argparse.ArgumentParser(description="The main entry point of the errbot.")
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="Full path to your config.py (default: config.py in current working directory).",
    )

    mode_selection = parser.add_mutually_exclusive_group()
    mode_selection.add_argument(
        "-v", "--version", action="version", version=f"Errbot version {VERSION}"
    )
    mode_selection.add_argument(
        "-r",
        "--restore",
        nargs="?",
        default=None,
        const="default",
        help="restore a bot from backup.py (default: backup.py from the bot data directory)",
    )
    mode_selection.add_argument(
        "-l", "--list", action="store_true", help="list all available backends"
    )
    mode_selection.add_argument(
        "--new-plugin",
        nargs="?",
        default=None,
        const="current_dir",
        help="create a new plugin in the specified directory",
    )
    mode_selection.add_argument(
        "-i",
        "--init",
        nargs="?",
        default=None,
        const=".",
        help="Initialize a simple bot minimal configuration in the optionally "
        "given directory (otherwise it will be the working directory). "
        "This will create a data subdirectory for the bot data dir and a plugins directory"
        " for your plugin development with an example in it to get you started.",
    )
    # storage manipulation
    mode_selection.add_argument(
        "--storage-set",
        nargs=1,
        help="DANGER: Delete the given storage namespace "
        "and set the python dictionary expression "
        "passed on stdin.",
    )
    mode_selection.add_argument(
        "--storage-merge",
        nargs=1,
        help="DANGER: Merge in the python dictionary expression "
        "passed on stdin into the given storage namespace.",
    )
    mode_selection.add_argument(
        "--storage-get",
        nargs=1,
        help="Dump the given storage namespace in a "
        "format compatible for --storage-set and "
        "--storage-merge.",
    )

    mode_selection.add_argument(
        "-T",
        "--text",
        dest="backend",
        action="store_const",
        const="Text",
        help="force local text backend",
    )

    if not ON_WINDOWS:
        option_group = parser.add_argument_group("optional daemonization arguments")
        option_group.add_argument(
            "-d",
            "--daemon",
            action="store_true",
            help="Detach the process from the console",
        )
        option_group.add_argument(
            "-p",
            "--pidfile",
            default=None,
            help="Specify the pid file for the daemon (default: current bot data directory)",
        )

    args = vars(parser.parse_args())  # create a dictionary of args

    if args["init"]:
        try:
            import pathlib
            import shutil

            import jinja2

            base_dir = (
                pathlib.Path.cwd()
                if args["init"] == "."
                else Path(args["init"]).resolve()
            )

            if not base_dir.exists():
                print(f"Target directory {base_dir} must exist. Please create it.")

            data_dir = base_dir / "data"
            extra_plugin_dir = base_dir / "plugins"
            extra_backend_plugin_dir = base_dir / "backend-plugins"
            example_plugin_dir = extra_plugin_dir / "err-example"
            log_path = base_dir / "errbot.log"

            templates_dir = Path(os.path.dirname(__file__)) / "templates" / "initdir"
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(templates_dir)), autoescape=True
            )
            config_template = env.get_template("config.py.tmpl")

            data_dir.mkdir(exist_ok=True)
            extra_plugin_dir.mkdir(exist_ok=True)
            extra_backend_plugin_dir.mkdir(exist_ok=True)
            example_plugin_dir.mkdir(exist_ok=True)

            with open(base_dir / "config.py", "w") as f:
                f.write(
                    config_template.render(
                        data_dir=str(data_dir),
                        extra_plugin_dir=str(extra_plugin_dir),
                        extra_backend_plugin_dir=str(extra_backend_plugin_dir),
                        log_path=str(log_path),
                    )
                )

            shutil.copyfile(
                templates_dir / "example.plug", example_plugin_dir / "example.plug"
            )
            shutil.copyfile(
                templates_dir / "example.py", example_plugin_dir / "example.py"
            )
            print("Your Errbot directory has been correctly initialized!")
            if base_dir == pathlib.Path.cwd():
                print('Just do "errbot" and it should start in text/development mode.')
            else:
                print(
                    f'Just do "cd {args["init"]}" then "errbot" and it should start in text/development mode.'
                )
            sys.exit(0)
        except Exception as e:
            print(f"The initialization of your errbot directory failed: {e}.")
            sys.exit(1)

    # This must come BEFORE the config is loaded below, to avoid printing
    # logs as a side effect of config loading.
    if args["new_plugin"]:
        directory = (
            os.getcwd() if args["new_plugin"] == "current_dir" else args["new_plugin"]
        )
        for handler in logging.getLogger().handlers:
            root_logger.removeHandler(handler)
        try:
            new_plugin_wizard(directory)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            sys.stderr.write(str(e) + "\n")
            sys.exit(1)
        finally:
            sys.exit(0)

    config_path = args["config"]
    # setup the environment to be able to import the config.py
    if config_path:
        # appends the current config in order to find config.py
        sys.path.insert(0, path.dirname(path.abspath(config_path)))
    else:
        config_path = execution_dir + sep + "config.py"

    config = get_config(config_path)  # will exit if load fails

    # Extra backend is expected to be a list type, convert string to list.
    extra_backend = getattr(config, "BOT_EXTRA_BACKEND_DIR", [])
    if isinstance(extra_backend, str):
        extra_backend = [extra_backend]
    ep = entry_point_plugins(group="errbot.backend_plugins")
    extra_backend.extend(ep)

    if args["list"]:
        from errbot.backend_plugin_manager import enumerate_backend_plugins

        print("Available backends:")
        roots = [CORE_BACKENDS] + extra_backend
        for backend in enumerate_backend_plugins(collect_roots(roots)):
            print(f"\t\t{backend.name}")
        sys.exit(0)

    def storage_action(namespace, fn):
        # Used to defer imports until it is really necessary during the loading time.
        from errbot.bootstrap import get_storage_plugin
        from errbot.storage import StoreMixin

        try:
            with StoreMixin() as sdm:
                sdm.open_storage(get_storage_plugin(config), namespace)
                fn(sdm)
            return 0
        except Exception as e:
            print(str(e), file=sys.stderr)
            return -3

    if args["storage_get"]:

        def p(sdm):
            print(repr(dict(sdm)))

        err_value = storage_action(args["storage_get"][0], p)
        sys.exit(err_value)

    if args["storage_set"]:

        def replace(sdm):
            new_dict = (
                _read_dict()
            )  # fail early and don't erase the storage if the input is invalid.
            sdm.clear()
            sdm.update(new_dict)

        err_value = storage_action(args["storage_set"][0], replace)
        sys.exit(err_value)

    if args["storage_merge"]:

        def merge(sdm):
            from deepmerge import always_merger

            new_dict = _read_dict()
            for key, value in new_dict.items():
                with sdm.mutable(key, {}) as conf:
                    always_merger.merge(conf, value)

        err_value = storage_action(args["storage_merge"][0], merge)
        sys.exit(err_value)

    if args["restore"]:
        backend = "Null"  # we don't want any backend when we restore
    elif args["backend"] is None:
        if not hasattr(config, "BACKEND"):
            log.fatal("The BACKEND configuration option is missing in config.py")
            sys.exit(1)
        backend = config.BACKEND
    else:
        backend = args["backend"]

    log.info(f"Selected backend {backend}.")

    # Check if at least we can start to log something before trying to start
    # the bot (esp. daemonize it).

    log.info(f"Checking for {config.BOT_DATA_DIR}...")
    if not path.exists(config.BOT_DATA_DIR):
        raise Exception(
            f'The data directory "{config.BOT_DATA_DIR}" for the bot does not exist.'
        )
    if not access(config.BOT_DATA_DIR, W_OK):
        raise Exception(
            f'The data directory "{config.BOT_DATA_DIR}" should be writable for the bot.'
        )

    if (not ON_WINDOWS) and args["daemon"]:
        if args["backend"] == "Text":
            raise Exception("You cannot run in text and daemon mode at the same time")
        if args["restore"]:
            raise Exception("You cannot restore a backup in daemon mode.")
        if args["pidfile"]:
            pid = args["pidfile"]
        else:
            pid = config.BOT_DATA_DIR + sep + "err.pid"

        # noinspection PyBroadException
        try:

            def action():
                from errbot.bootstrap import bootstrap

                bootstrap(backend, root_logger, config)

            daemon = Daemonize(app="err", pid=pid, action=action, chdir=os.getcwd())
            log.info("Daemonizing")
            daemon.start()
        except Exception:
            log.exception("Failed to daemonize the process")
        exit(0)
    from errbot.bootstrap import bootstrap

    restore = args["restore"]
    if restore == "default":  # restore with no argument, get the default location
        restore = path.join(config.BOT_DATA_DIR, "backup.py")

    bootstrap(backend, root_logger, config, restore)
    log.info("Process exiting")


if __name__ == "__main__":
    main()
