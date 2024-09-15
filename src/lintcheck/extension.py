"""Lint Check IDLE Extension."""

# Programmed by CoolCat467

from __future__ import annotations

# Lint Check - Use pylint to check open file, then add comments to file.
# Copyright (C) 2023-2024  CoolCat467
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__title__ = "extension"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"

import os
import traceback
from typing import TYPE_CHECKING, Any, ClassVar

from pylint.lint import Run as run_pylint  # noqa: N813

from lintcheck import utils

if TYPE_CHECKING:
    from idlelib.pyshell import PyShellEditorWindow
    from tkinter import Event

    import pylint


class Reporter:
    """Reporter class."""

    __slots__ = ("linter", "messages")

    def __init__(self) -> None:
        """Initialize reporter."""
        self.linter: pylint.lint.pylinter.PyLinter | None = None
        self.messages: list[dict[str, str | int]] = []

    def handle_message(self, msg: pylint.message.message.Message) -> None:
        """Record message."""
        # Convert message object into dictionary
        data: dict[str, str | int] = {}
        for attr in ("abspath", "column", "line", "msg", "msg_id", "symbol"):
            data[attr] = getattr(msg, attr)
        # Save message
        self.messages.append(data)

    def on_set_current_module(self, modname: str, filepath: str) -> None:
        """Handle module starts to be analysed."""

    def display_messages(
        self,
        section: pylint.reporters.ureports.nodes.Section,
    ) -> None:
        """Handle displaying the messages of the reporter."""

    def on_close(
        self,
        stats: pylint.utils.linterstats.LinterStats,
        previous_stats: pylint.utils.linterstats.LinterStats,
    ) -> None:
        """Handle when a module finished analyzing."""

    def display_reports(
        self,
        section: pylint.reporters.ureports.nodes.Section,
    ) -> None:
        """Display results encapsulated in the layout tree."""

    def get_messages(self) -> list[dict[str, str | int]]:
        """Return Messages."""
        return self.messages


def parse_comments(
    comments: list[dict[str, str | int]],
) -> dict[str, list[utils.Comment]]:
    """Get list of message dictionaries from pylint output."""
    files: dict[str, list[utils.Comment]] = {}

    for comment in comments:
        path = comment["abspath"]
        assert isinstance(path, str)
        filename = os.path.abspath(path)
        files.setdefault(filename, [])

        head = f"{comment['symbol']} ({comment['msg_id']}): "
        message_lines = comment["msg"]
        assert isinstance(message_lines, str)
        line = comment["line"]
        assert isinstance(line, int)
        column = comment["column"]
        assert isinstance(column, int)
        for idx, msg in enumerate(reversed(message_lines.splitlines())):
            message = utils.Comment(
                file=filename,
                line=line,
                column=column,
                contents=msg if idx != 0 else f"{head}{msg}",
            )

            files[filename].append(message)
    return files


# Important weird: If event handler function returns 'break',
# then it prevents other bindings of same event type from running.
# If returns None, normal and others are also run.


class lintcheck(utils.BaseExtension):  # noqa: N801
    """Add comments from pylint to an open program."""

    __slots__ = ()
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

    # Overwritten in reload
    ignore = ""
    jobs = "0"
    search_wrap = "False"

    def __init__(self, editwin: PyShellEditorWindow) -> None:
        """Initialize the settings for this extension."""
        super().__init__(editwin, comment_prefix="lintcheck")
        # pylint: disable=C0401

    @property
    def lintcomment_only_current_file(self) -> bool:
        """Should only add lint comments for currently open file?."""
        return True

    def add_lint_comments_for_file(
        self,
        comments: list[utils.Comment],
    ) -> dict[str, list[int]]:
        """Add lint comments for target files.

        Return list of lines were a comment was added.
        """
        # Split up comments by line in order
        line_data: dict[int, list[utils.Comment]] = {}
        for comment in comments:
            line_data.setdefault(comment.line, [])
            line_data[comment.line].append(comment)

        all_messages = []
        for line in sorted(line_data):
            messages = line_data[line]
            if not messages:
                continue
            all_messages.extend(messages)
            pointers = self.get_pointers(messages)
            if pointers is not None:
                all_messages.append(pointers)

        return self.add_comments(all_messages)

    def lint_check_add_response_comments(
        self,
        lint_messages: list[dict[str, str | int]],
        only_filename: str | None = None,
    ) -> dict[str, list[int]]:
        """Add comments for each line given in lint_messages.

        Return list of lines where comments were added.
        """
        assert self.files.filename is not None

        if only_filename is not None:
            only_filename = os.path.abspath(only_filename)

        start_line = self.editwin.getlineno()

        files = parse_comments(lint_messages)

        file_commented_lines: dict[str, list[int]] = {}

        to_comment = list(files)

        if self.lintcomment_only_current_file:
            assert only_filename is not None
            to_comment = [only_filename]

            # Find first line in target file or use start_line
            if not files.get(only_filename):
                other_files_comment_line = start_line
            else:
                other_files_comment_line = min(
                    comment.line for comment in files[only_filename]
                )

            # Add comments about how other files have errors
            files.setdefault(only_filename, [])
            for filename in files:
                if filename == only_filename:
                    continue
                files[only_filename].append(
                    utils.Comment(
                        file=only_filename,
                        line=other_files_comment_line,
                        contents=f"Another file has errors: {filename!r}",
                        column_end=0,
                    ),
                )

        for target_filename in to_comment:
            if target_filename not in files:
                continue
            file_comments = self.add_lint_comments_for_file(
                files[target_filename],
            )
            file_commented_lines.update(file_comments)
        return file_commented_lines

    def initial(self) -> tuple[str | None, str | None]:
        """Do common initial setup. Return error or none, file.

        Reload configuration, make sure file is saved,
        and make sure mypy is installed
        """
        # Reload configuration
        self.reload()

        # Get file we are checking
        raw_filename: str | None = self.files.filename
        if raw_filename is None:
            return "break", None
        file: str = os.path.abspath(raw_filename)

        # Make sure file is saved.
        if not self.files.get_saved():
            if not utils.ask_save_dialog(self.text):
                # If not ok to save, do not run. Would break file.
                self.text.bell()
                return "break", file
            # Otherwise, we are clear to save
            self.files.save(None)
            if not self.files.get_saved():
                return "break", file

        # Everything worked
        return None, file

    def lint_check_event(self, event: Event[Any] | None = None) -> str:
        """Perform a pylint check and add comments."""
        # pylint: disable=unused-argument
        init_return, file = self.initial()

        if init_return is not None:
            return init_return

        if file is None:
            return "break"

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
        try:
            run_pylint(
                args,
                reporter=reporter,  # type: ignore[arg-type]
                exit=False,
            )
        except SystemExit as exc:
            traceback.print_exception(exc)
            return "break"

        # Add code comments
        self.lint_check_add_response_comments(reporter.get_messages(), file)

        # Make bell sound so user knows we are done,
        # as it freezes a bit while pylint looks at the file
        self.text.bell()
        return "break"

    def remove_lint_comments_event(self, _event: Event[Any]) -> str:
        """Remove selected extension comments."""
        self.remove_selected_extension_comments()
        return "break"

    def remove_all_lint_comments(self, _event: Event[Any]) -> str:
        """Remove all extension comments."""
        self.remove_all_extension_comments()
        return "break"

    def find_next_lint_comment_event(self, _event: Event[Any]) -> str:
        """Find next extension comment by hacking the search dialog engine."""
        # Reload configuration
        self.reload()

        # Find comment
        self.find_next_extension_comment(self.search_wrap == "True")

        return "break"

    # def close(self) -> None:
    #     """Extension cleanup before IDLE window closes."""
