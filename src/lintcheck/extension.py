#!/usr/bin/env python3
# Lint Check - Use pylint to check open file, then add comments to file.

"Lint Check Extension"

# Programmed by CoolCat467

from __future__ import annotations

__title__ = "lintcheck"
__author__ = "CoolCat467"
__license__ = "GPLv3"
__version__ = "0.3.2"
__ver_major__ = 0
__ver_minor__ = 3
__ver_patch__ = 2

import os
import sys
from functools import wraps
from idlelib import search, searchengine
from idlelib.config import idleConf
from idlelib.pyshell import PyShellEditorWindow
from tkinter import Event, Tk, messagebox
from typing import Any, Callable, ClassVar, TypeVar, cast

_HAS_LINT = True
try:
    import pylint.lint.run
except ImportError:
    print(f"{__file__}: Pylint not installed!")
    _HAS_LINT = False


def get_required_config(
    values: dict[str, str],
    bind_defaults: dict[str, str],
) -> str:
    """Get required configuration file data."""
    config = ""
    # Get configuration defaults
    settings = "\n".join(
        f"{key} = {default}" for key, default in values.items()
    )
    if settings:
        config += f"\n[{__title__}]\n{settings}"
        if bind_defaults:
            config += "\n"
    # Get key bindings data
    settings = "\n".join(
        f"{event} = {key}" for event, key in bind_defaults.items()
    )
    if settings:
        config += f"\n[{__title__}_cfgBindings]\n{settings}"
    return config


def check_installed() -> bool:
    """Make sure extension installed."""
    # Get list of system extensions
    extensions = set(idleConf.defaultCfg["extensions"])

    # Do we have the user extend extension?
    has_user = "idleuserextend" in idleConf.GetExtensions(active_only=True)

    # If we don't, things get messy and we need to change the root config file
    ex_defaults = idleConf.defaultCfg["extensions"].file
    if has_user:
        # Otherwise, idleuserextend patches IDLE and we only need to modify
        # the user config file
        ex_defaults = idleConf.userCfg["extensions"].file
        extensions |= set(idleConf.userCfg["extensions"])

    # Import this extension (this file),
    module = __import__(__title__)

    # Get extension class
    if not hasattr(module, __title__):
        print(
            f"ERROR: Somehow, {__title__} was installed improperly, "
            f"no {__title__} class found in module. Please report "
            "this on github.",
            file=sys.stderr,
        )
        sys.exit(1)

    cls = getattr(module, __title__)

    # Get extension class keybinding defaults
    required_config = get_required_config(
        getattr(cls, "values", {}),
        getattr(cls, "bind_defaults", {}),
    )

    # If this extension not in there,
    if __title__ not in extensions:
        # Tell user how to add it to system list.
        print(f"{__title__} not in system registered extensions!")
        print(
            f"Please run the following command to add {__title__} "
            + "to system extensions list.\n",
        )
        # Make sure line-breaks will go properly in terminal
        add_data = required_config.replace("\n", "\\n")
        # Tell them the command
        append = "| sudo tee -a"
        if has_user:
            append = ">>"
        print(f"echo -e '{add_data}' {append} {ex_defaults}\n")
    else:
        print(f"Configuration should be good! (v{__version__})")
        return True
    return False


class Reporter:
    "Reporter class"
    __slots__ = ("linter", "messages")

    def __init__(self) -> None:
        self.linter: pylint.lint.pylinter.PyLinter = None
        self.messages: list[dict[str, str | int]] = []

    def handle_message(self, msg: pylint.message.message.Message) -> None:
        "Record message"
        # Convert message object into dictionary
        data: dict[str, Any] = {}
        for attr in ("abspath", "column", "line", "msg", "msg_id", "symbol"):
            data[attr] = getattr(msg, attr)
        # Save message
        self.messages.append(data)

    def on_set_current_module(self, modname: str, filepath: str) -> None:
        "on_set_current_module"

    def display_messages(
        self, section: pylint.reporters.ureports.nodes.Section
    ) -> None:
        "display_messages"

    def on_close(
        self,
        stats: pylint.utils.linterstats.LinterStats,
        previous_stats: pylint.utils.linterstats.LinterStats,
    ) -> None:
        "on_close"

    def display_reports(
        self, section: pylint.reporters.ureports.nodes.EvaluationSection
    ) -> None:
        "display_reports"

    def get_messages(self) -> list[dict[str, str | int]]:
        "Return Messages"
        return self.messages


def get_line_selection(line: int) -> tuple[str, str]:
    "Get selection strings for given line"
    return f"{line}.0", f"{line+1}.0"


def get_line_indent(text: str, char: str = " ") -> int:
    "Return line indent."
    for idx, cur in enumerate(text.split(char)):
        if cur != "":
            return idx
    return 0


F = TypeVar("F", bound=Callable[..., Any])


def undo_block(func: F) -> F:
    "Mark block of edits as a single undo block."

    @wraps(func)
    def undo_wrapper(self: lintcheck, *args: Any, **kwargs: Any) -> Any:
        "Wrap function in start and stop undo events."
        self.text.undo_block_start()
        result = func(self, *args, **kwargs)
        self.text.undo_block_stop()
        return result

    return cast(F, undo_wrapper)


def ensure_section_exists(section: str) -> bool:
    """Ensure section exists in user extensions configuration.

    Returns True if edited.
    """
    if section not in idleConf.GetSectionList("user", "extensions"):
        idleConf.userCfg["extensions"].AddSection(section)
        return True
    return False


def ensure_values_exist_in_section(
    section: str,
    values: dict[str, str],
) -> bool:
    """For each key in values, make sure key exists. Return if edited.

    If not, create and set to value.
    """
    need_save = False
    for key, default in values.items():
        value = idleConf.GetOption(
            "extensions",
            section,
            key,
            warn_on_default=False,
        )
        if value is None:
            idleConf.SetOption("extensions", section, key, default)
            need_save = True
    return need_save


def get_search_engine_params(
    engine: searchengine.SearchEngine,
) -> dict[str, str | bool]:
    "Get current search engine parameters"
    return {
        name: getattr(engine, f"{name}var").get()
        for name in ("pat", "re", "case", "word", "wrap", "back")
    }


def set_search_engine_params(
    engine: searchengine.SearchEngine, data: dict[str, str | bool]
) -> None:
    "Get current search engine parameters"
    for name in ("pat", "re", "case", "word", "wrap", "back"):
        if name in data:
            getattr(engine, f"{name}var").set(data[name])


# Important weird: If event handler function returns 'break',
# then it prevents other bindings of same event type from running.
# If returns None, normal and others are also run.


class lintcheck:  # pylint: disable=invalid-name
    "Add comments from pylint to an open program."
    __slots__ = ("editwin", "text", "formatter", "files")
    # Extend the file and format menus.
    menudefs: ClassVar = [
        (
            "edit",
            [
                None,
                ("_Lint Check File", "<<lint-check>>"),
                ("Find Next Lint Comment", "<<find-next-lint-comment>>"),
            ],
        ),
        ("format", [("R_emove Lint Comments", "<<remove-lint-comments>>")]),
    ]
    # Default values for configuration file
    values: ClassVar = {
        "enable": "True",
        "enable_editor": "True",
        "enable_shell": "False",
        "ignore": "None",
        "jobs": "0",
        "search_wrap": "False",
    }
    # Default key-binds for configuration file
    bind_defaults: ClassVar = {
        "lint-check": "<Control-Shift-Key-C>",
        "remove-lint-comments": "<Control-Alt-Key-c>",
        "find-next-lint-comment": "<Alt-Key-c>",
    }
    comment = "# lintcheck: "

    # Overwritten in reload
    ignore = ""
    jobs = "0"
    search_wrap = "False"

    def __init__(self, editwin: PyShellEditorWindow) -> None:
        "Initialize the settings for this extension."
        # pylint: disable=C0401
        self.editwin = editwin  # idlelib.pyshell.PyShellEditorWindow
        self.text = editwin.text  # idlelib.multicall.MultiCallCreator
        self.formatter = editwin.fregion  # idlelib.format.FormatRegion
        # self.flist     = editwin.flist#idlelib.pyshell.PyShellFileList
        self.files = editwin.io  # idlelib.iomenu.IOBinding

        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            if attr_name.endswith("_event"):
                bind_name = "-".join(attr_name.split("_")[:-1]).lower()
                self.text.bind(f"<<{bind_name}>>", getattr(self, attr_name))
                # print(f'{attr_name} -> {bind_name}')

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.editwin!r})"

    @classmethod
    def ensure_bindings_exist(cls) -> bool:
        """Ensure key bindings exist in user extensions configuration.

        Return True if need to save.
        """
        if not cls.bind_defaults:
            return False

        need_save = False
        section = f"{cls.__name__}_cfgBindings"
        if ensure_section_exists(section):
            need_save = True
        if ensure_values_exist_in_section(section, cls.bind_defaults):
            need_save = True
        return need_save

    @classmethod
    def ensure_config_exists(cls) -> bool:
        """Ensure required configuration exists for this extension.

        Return True if need to save.
        """
        need_save = False
        if ensure_section_exists(cls.__name__):
            need_save = True
        if ensure_values_exist_in_section(cls.__name__, cls.values):
            need_save = True
        return need_save

    @classmethod
    def reload(cls) -> None:
        """Load class variables from configuration."""
        # Ensure file default values exist so they appear in settings menu
        save = cls.ensure_config_exists()
        if cls.ensure_bindings_exist() or save:
            idleConf.SaveUserCfgFiles()

        # Reload configuration file
        idleConf.LoadCfgFiles()

        # Reload configuration file
        idleConf.LoadCfgFiles()

        # For all possible configuration values
        for key, default in cls.values.items():
            # Set attribute of key name to key value from configuration file
            if key not in {"enable", "enable_editor", "enable_shell"}:
                value = idleConf.GetOption(
                    "extensions",
                    cls.__name__,
                    key,
                    default=default,
                )
                setattr(cls, key, value)

    def get_msg_line(self, indent: int, msg: str) -> str:
        "Return message line given indent and message."
        strindent = " " * indent
        return f"{strindent}{self.comment}{msg}"

    def get_line(self, line: int) -> str:
        "Get the characters from the given line in the currently open file."
        chars: str = self.text.get(*get_line_selection(line))
        return chars

    def comment_exists(self, line: int, text: str) -> bool:
        "Return True if comment for message already exists on line."
        return self.get_msg_line(0, text) in self.get_line(line - 1)

    def add_comment(
        self, message: dict[str, str | int], max_exist_up: int = 0
    ) -> bool:
        "Return True if added new comment, False if already exists."
        # Get line and message from output
        # file = str(message['file'])
        line: int = int(message["line"])
        msg: str = str(message["message"])

        # If there is already a comment from us there, ignore that line.
        # +1-1 is so at least up by 1 is checked, range(0) = []
        for i in range(max_exist_up + 1):
            if self.comment_exists(line - (i - 1), msg):
                return False

        # Get line checker is talking about
        chars = self.get_line(line)

        # Figure out line indent
        indent = get_line_indent(chars)

        # Add comment line
        chars = self.get_msg_line(indent, msg) + "\n" + chars

        # Save changes
        start, end = get_line_selection(line)
        self.text.delete(start, end)
        self.text.insert(start, chars, ())
        return True

    @staticmethod
    def parse_comments(
        comments: list[dict[str, str | int]]
    ) -> dict[str, list[dict[str, str | int]]]:
        "Get list of message dictionaries from pylint output."
        files: dict[str, list[dict[str, str | int]]] = {}

        for comment in comments:
            path = comment["abspath"]
            assert isinstance(path, str)
            filename = os.path.abspath(path)
            if filename not in files:
                files[filename] = []

            head = f"{comment['symbol']} ({comment['msg_id']}): "
            message_lines = comment["msg"]
            assert isinstance(message_lines, str)
            for idx, msg in enumerate(reversed(message_lines.splitlines())):
                files[filename].append(
                    {
                        "file": filename,
                        "column": comment["column"],
                        "line": comment["line"],
                        "message": msg if idx != 0 else f"{head}{msg}",
                    }
                )
        return files

    def get_pointers(
        self, messages: list[dict[str, int | str]]
    ) -> dict[str, int | str] | None:
        "Return message pointing to message column position"
        line = int(messages[0]["line"]) + 1

        # Figure out line intent
        line_text = self.get_line(line)
        indent = get_line_indent(line_text)
        line_len = len(line_text)

        columns: set[int] = set()
        lastcol = len(self.comment) + indent + 1

        for message in messages:
            start = int(message["column"])
            end = int(message.get("column_end", start + lastcol)) - lastcol
            for col in range(start, end + 1):
                columns.add(col)

        new_line = ""
        for col in sorted(columns):
            if col > line_len:
                break
            spaces = col - lastcol - 1
            new_line += " " * spaces + "^"
            lastcol = col

        if not new_line.strip():
            return None

        return {"line": line, "message": new_line, "column": lastcol}

    def add_comments(
        self,
        target_filename: str,
        start_line: int,
        lint_messages: list[dict[str, str | int]],
    ) -> list[int]:
        "Add comments for each line given in lint_messages, from bottom to top."
        files = self.parse_comments(lint_messages)

        # Only handling messages for target filename
        line_data: dict[int, list[dict[str, Any]]] = {}
        if target_filename in files:
            for message in files[target_filename]:
                line = message["line"]
                assert isinstance(line, int), "Line must be int"
                if line not in line_data:
                    line_data[line] = []
                line_data[line].append(message)

        line_order: list[int] = list(sorted(line_data, reverse=True))
        first: int = line_order[-1] if line_order else start_line

        if first not in line_data:  # if used starting line
            line_data[first] = []
            line_order.append(first)

        for filename in {f for f in files if f != target_filename}:
            line_data[first].append(
                {
                    "file": target_filename,
                    "line": first,
                    "column": 0,
                    "message": f"Another file has errors: {filename}",
                }
            )

        comments = []
        for line in line_order:
            messages = line_data[line]
            if not messages:
                continue
            # pointers = self.get_pointers(messages)
            # if pointers is not None:
            #    messages.append(pointers)

            total = len(messages)
            for message in sorted(messages, key=lambda m: int(m["column"])):
                # for message in reversed(messages):
                if self.add_comment(message, total):
                    comments.append(line)
        return comments

    def ask_save_dialog(self) -> bool:
        "Ask to save dialog stolen from idlelib.runscript.ScriptBinding"
        msg = "Source Must Be Saved\n" + 5 * " " + "OK to Save?"
        confirm: bool = messagebox.askokcancel(
            title="Save Before Run or Check",
            message=msg,
            default=messagebox.OK,
            parent=self.text,
        )
        return confirm

    def initial(self) -> tuple[str | None, str, int]:
        """Do common initial setup. Return error or none, file, and start line

        Reload configuration, make sure file is saved,
        and make sure mypy is installed"""
        self.reload()

        # Get file we are checking
        file: str = os.path.abspath(self.files.filename)

        # Remember where we started
        start_line_no: int = self.editwin.getlineno()

        if not _HAS_LINT:
            self.add_comment(
                {
                    "file": file,
                    "line": start_line_no,
                    "message": "Could not import pylint. "
                    "Please install pylint and restart IDLE to use this extension.",
                },
                start_line_no,
            )

            # Make bell sound so user knows they need to pay attention
            self.text.bell()
            return "break", file, start_line_no

        # Make sure file is saved.
        if not self.files.get_saved():
            if not self.ask_save_dialog():
                # If not ok to save, do not run. Would break file.
                self.text.bell()
                return "break", file, start_line_no
            # Otherwise, we are clear to save
            self.files.save(None)
            self.files.set_saved(True)

        # Everything worked
        return None, file, start_line_no

    @undo_block
    def lint_check_event(self, event: Event[Any] | None = None) -> str:
        "Perform a pylint check and add comments."
        # pylint: disable=unused-argument
        init_return, file, start_line_no = self.initial()

        if init_return is not None:
            return init_return

        # Get arguments
        try:
            jobs = int(self.jobs)
        except ValueError:
            jobs = 0
        jobs = max(0, jobs)
        args = [file, f"--jobs={jobs}"]
        if self.ignore and self.ignore != "None":
            if ";" not in self.ignore:
                ignore = [self.ignore]
            else:
                ignore = self.ignore.split(";")
            args.append("--disable=" + ",".join(ignore))

        # Run pylint on open file
        reporter = Reporter()
        pylint.lint.run.Run(args, reporter=reporter, exit=False)

        # Add code comments
        self.add_comments(file, start_line_no, reporter.get_messages())

        # Make bell sound so user knows we are done,
        # as it freezes a bit while pylint looks at the file
        self.text.bell()
        return "break"

    def remove_lint_comments_event(
        self, event: Event[Any] | None = None
    ) -> str:
        "Remove selected pylint comments."
        # pylint: disable=unused-argument
        # Get selected region lines
        head, tail, chars, lines = self.formatter.get_region()
        if self.comment not in chars:
            # Make bell sound so user knows this ran even though
            # nothing happened.
            self.text.bell()
            return "break"
        # Using dict so we can reverse and enumerate
        ldict = dict(enumerate(lines))
        for idx in sorted(ldict.keys(), reverse=True):
            line = ldict[idx]
            # If after indent there is mypy comment
            if line.lstrip().startswith(self.comment):
                # If so, remove line
                del lines[idx]
        # Apply changes
        self.formatter.set_region(head, tail, chars, lines)
        return "break"

    @undo_block
    def remove_all_lint_comments(self, event: Event[Any]) -> str:
        "Remove all mypy comments."
        # pylint: disable=unused-argument
        eof_idx = self.text.index("end")

        chars = self.text.get("0.0", eof_idx)

        lines = chars.splitlines()
        modified = False
        for idx in reversed(range(len(lines))):
            if lines[idx].lstrip().startswith(self.comment):
                del lines[idx]
                modified = True
        if not modified:
            return "break"

        chars = "\n".join(lines)

        # Apply changes
        self.text.delete("0.0", eof_idx)
        self.text.insert("0.0", chars, None)
        return "break"

    def find_next_lint_comment_event(
        self, event: Event[Any] | None = None
    ) -> str:
        "Find next comment by hacking the search dialog engine."
        # pylint: disable=unused-argument
        self.reload()

        root: Tk
        root = self.text._root()  # pylint: disable=protected-access

        # Get search engine singleton from root
        engine: searchengine.SearchEngine = searchengine.get(root)

        # Get current search prams
        global_search_params = get_search_engine_params(engine)

        # Set search pattern to comment starter
        set_search_engine_params(
            engine,
            {
                "pat": f"^\\s*{self.comment}",
                "re": True,
                "case": True,
                "word": False,
                "wrap": self.search_wrap == "True",
                "back": False,
            },
        )

        # Find current pattern
        search.find_again(self.text)

        # Re-apply previous search prams
        set_search_engine_params(engine, global_search_params)
        return "break"


lintcheck.reload()

if __name__ == "__main__":
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    check_installed()
