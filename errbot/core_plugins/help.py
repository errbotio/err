import textwrap

from dulwich import errors as dulwich_errors

from errbot import BotPlugin, botcmd
from errbot.utils import git_tag_list
from errbot.version import VERSION


class Help(BotPlugin):
    MSG_HELP_TAIL = (
        "Type help <command name> to get more info " "about that specific command."
    )
    MSG_HELP_UNDEFINED_COMMAND = "That command is not defined."

    def is_git_directory(self, path="."):
        try:
            tags = git_tag_list(path)
        except dulwich_errors.NotGitRepository:
            tags = None
        except Exception as _:
            # we might want to handle other exceptions another way. For now leaving this general
            tags = None

        return tags.pop(-1) if tags is not None else None

    def may_access_command(self, m, cmd):
        m, _, _ = self._bot._process_command_filters(
            msg=m, cmd=cmd, args=None, dry_run=True
        )
        return m is not None

    # noinspection PyUnusedLocal
    @botcmd(template="about")
    def about(self, msg, args):
        """Return information about this Errbot instance and version"""
        git_version = self.is_git_directory()
        if git_version:
            return dict(version=f"{git_version.decode('utf-8')} GIT CHECKOUT")
        else:
            return {"version": VERSION}

    # noinspection PyUnusedLocal
    @botcmd
    def apropos(self, msg, args):
        """Returns a help string listing available options.

        Automatically assigned to the "help" command."""
        if not args:
            return "Usage: " + self._bot.prefix + "apropos search_term"

        description = "Available commands:\n"

        cls_commands = {}
        for name, command in self._bot.all_commands.items():
            cls = self._bot.get_plugin_class_from_method(command)
            cls = str.__module__ + "." + cls.__name__  # makes the fuul qualified name
            commands = cls_commands.get(cls, [])
            if (
                not self.bot_config.HIDE_RESTRICTED_COMMANDS
                or self.may_access_command(msg, name)
            ):
                commands.append((name, command))
                cls_commands[cls] = commands

        usage = ""
        for cls in sorted(cls_commands):
            commands = []
            for name, command in cls_commands[cls]:
                if name == "help":
                    continue

                if command._err_command_hidden:
                    continue

                doc = command.__doc__

                if doc is not None and args.lower() not in doc.lower():
                    continue

                name_with_spaces = name.replace("_", " ", 1)
                doc = (doc or "(undocumented)").strip().split("\n", 1)[0]
                commands.append("\t" + self._bot.prefix + name_with_spaces + ": " + doc)

            usage += "\n".join(commands)
        usage += "\n\n"

        return "".join(filter(None, [description, usage])).strip()

    @botcmd
    def help(self, msg, args):
        """Returns a help string listing available options.
        Automatically assigned to the "help" command."""

        # Normalize args to lowercase for ease of use
        args = args.lower() if args else ""
        usage = ""
        description = "### All commands\n"

        cls_obj_commands = {}
        for name, command in self._bot.all_commands.items():
            cls = self._bot.get_plugin_class_from_method(command)
            obj = command.__self__
            _, commands = cls_obj_commands.get(cls, (None, []))
            if (
                not self.bot_config.HIDE_RESTRICTED_COMMANDS
                or self.may_access_command(msg, name)
            ):
                commands.append((name, command))
                cls_obj_commands[cls] = (obj, commands)

        # show all
        if not args:
            for cls in sorted(
                cls_obj_commands.keys(), key=lambda c: cls_obj_commands[c][0].name
            ):
                obj, commands = cls_obj_commands[cls]
                name = obj.name
                # shows class and description
                usage += f"\n**{name}**\n\n"
                if getattr(cls.__errdoc__, "strip", None):
                    usage += f"{cls.__errdoc__.strip()}\n\n"
                else:
                    usage += cls.__errdoc__ or "\n\n"

                for name, command in sorted(commands):
                    if command._err_command_hidden:
                        continue
                    # show individual commands
                    usage += self._cmd_help_line(name, command)
            usage += "\n\n"  # end cls section
        elif args:
            for cls, (obj, cmds) in cls_obj_commands.items():
                if obj.name.lower() == args:
                    break
            else:
                cls, obj, cmds = None, None, None

            if cls is None:
                # Plugin not found.
                description = ""
                all_commands = dict(self._bot.all_commands)
                all_commands.update(
                    {k.replace("_", " "): v for k, v in all_commands.items()}
                )
                if args in all_commands:
                    usage += self._cmd_help_line(args, all_commands[args], True)
                else:
                    usage += self.MSG_HELP_UNDEFINED_COMMAND
            else:
                # filter out the commands related to this class
                description = ""
                description += f"\n**{obj.name}**\n\n"
                if getattr(cls.__errdoc__, "strip", None):
                    description += f"{cls.__errdoc__.strip()}\n\n"
                else:
                    description += cls.__errdoc__ or "\n\n"
                pairs = []
                for name, command in cmds:
                    if self.bot_config.HIDE_RESTRICTED_COMMANDS:
                        if command._err_command_hidden:
                            continue

                        if not self.may_access_command(msg, name):
                            continue
                    pairs.append((name, command))

                pairs = sorted(pairs)

                for name, command in pairs:
                    usage += self._cmd_help_line(name, command)

        return "".join(filter(None, [description, usage]))

    def _cmd_help_line(self, name, command, show_doc=False):
        """
        Returns:
            str. a single line indicating the help representation of a command.
        """
        cmd_name = name.replace("_", " ")
        cmd_doc = textwrap.dedent(self._bot.get_doc(command)).strip()
        prefix = (
            self._bot.prefix
            if getattr(command, "_err_command_prefix_required", True)
            else ""
        )

        name = cmd_name
        patt = getattr(command, "_err_command_re_pattern", None)

        if patt:
            re_help_name = getattr(command, "_err_command_re_name_help", None)
            name = re_help_name if re_help_name else patt.pattern

        if not show_doc:
            cmd_doc = cmd_doc.split("\n")[0]

            if len(cmd_doc) > 80:
                cmd_doc = f"{cmd_doc[:77]}..."

        help_str = f"- **{prefix}{name}** - {cmd_doc}\n"

        return help_str
