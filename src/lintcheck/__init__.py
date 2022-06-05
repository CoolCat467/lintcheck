#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Lint Check - Use pylint to check open file, then add comments to file.

"Lint Check Extension"

# Programmed by CoolCat467

__title__ = 'lintcheck'
__author__ = 'CoolCat467'
__license__ = 'GPLv3'
__version__ = '0.2.0'
__ver_major__ = 0
__ver_minor__ = 2
__ver_patch__ = 0

from typing import Any, Callable, TypeVar, cast

import os
import json
from functools import wraps

from tkinter import messagebox

from idlelib.config import idleConf# type: ignore
from idlelib import search# type: ignore

_HAS_LINT = True
try:
    import pylint.lint.run# type: ignore
except ImportError:
    print(f'{__file__}: Pylint not installed!')
    _HAS_LINT = False

def check_installed() -> bool:
    "Make sure extension installed."
    # Get list of system extensions
    extensions = list(idleConf.defaultCfg['extensions'])
    # If this extension not in there,
    if __title__ not in extensions:
        # Tell user how to add it to system list.
        print(f'{__title__} not in system registered extensions!')
        print(f'Please run the following command to add {__title__} to system extensions list.\n')
        ex_defaults = idleConf.defaultCfg['extensions'].file

        # Import this extension (this file),
        try:
            module = __import__(__title__)
        except ModuleNotFoundError:
            print(f'{__title__} is not installed!')
            return False
        # Get extension class
        if hasattr(module, __title__):
            cls = getattr(module, __title__)
            # Get extension class keybinding defaults
            add_data = ''
            if hasattr(cls, 'values'):
                # Get config defaults
                values = '\n'.join(f'{key} = {default}' for key, default in cls.values.items())
                # Add to add_data
                add_data += f"\n[{__title__}]\n{values}"
            if hasattr(cls, 'bind_defaults'):
                # Get keybindings data
                values = '\n'.join(f'{event} = {key}' for event, key in cls.bind_defaults.items())
                # Add to add_data
                add_data += f"\n[{__title__}_cfgBindings]\n{values}"
            # Make sure linebreaks will go properly in terminal
            add_data = add_data.replace('\n', '\\n')
            # Tell them command
            print(f"echo -e '{add_data}' | sudo tee -a {ex_defaults}")
            print()
        else:
            print(f'ERROR: Somehow, {__title__} was installed improperly, no {__title__} class '\
                  'found in module. Please report this on github.\n')
    else:
        print('Config should be good!')
        return True
    return False

def get_line_indent(text: str, char: str=' ') -> int:
    "Return line indent."
    idx = 0
    for idx, cur in enumerate(text.split(char)):
        if cur != '':
            break
    return idx

def ensure_section_exists(section: str) -> bool:
    "Ensure section exists in user extensions config. Return True if created."
    if not section in idleConf.GetSectionList('user', 'extensions'):
        idleConf.userCfg['extensions'].AddSection(section)
        return True
    return False

F = TypeVar('F', bound=Callable[..., Any])

def undo_block(func: F) -> F:
    "Mark block of edits as a single undo block."
    @wraps(func)
    def undo_wrapper(self, *args, **kwargs):
        "Wrap function in start and stop undo events."
        self.text.undo_block_start()
        result = func(self, *args, **kwargs)
        self.text.undo_block_stop()
        return result
    return cast(F, undo_wrapper)

def ensure_values_exist_in_section(section: str, values: dict) -> bool:
    "For each key in values, make sure key exists. If not, create and set to value. "\
         "Return True if created any defaults."
    need_save = False
    for key, default in values.items():
        value = idleConf.GetOption('extensions', section, key,
                                   warn_on_default=False)
        if value is None:
            idleConf.SetOption('extensions', section, key, default)
            need_save = True
    return need_save

# Important weird: If event handler function returns 'break',
# then it prevents other bindings of same event type from running.
# If returns None, normal and others are also run.

class lintcheck:# pylint: disable=C0103
    "Add comments from pylint to an open program."
    # Extend the file and format menus.
    menudefs = [
        ('file', [
            ('_Lint Check File', '<<lint-check>>')
        ] ),
        ('format', [
            ('R_emove Lint Comments', '<<remove-lint-comments>>')
        ] )
    ]
    # Default values for config file
    values = {'enable': 'True',
              'enable_editor': 'True',
              'enable_shell': 'False',
              'ignore': 'None',
              'jobs': '0',
              'search_wrap': 'False'}
    # Default keybinds for config file
    bind_defaults = {'lint-check': '<Control-Shift-Key-C>',
                     'remove-lint-comments': '<Control-Alt-Key-c>',
                     'find-next-lint-comment': '<Alt-Key-c>'}
    comment = '# lintcheck: '

    # Overwritten in reload
    ignore = ''
    jobs = '0'
    search_wrap = 'False'

    def __init__(self, editwin):
        "Initialize the settings for this extension."
        self.editwin = editwin#idlelib.pyshell.PyShellEditorWindow
        self.text = editwin.text#idlelib.multicall.MultiCallCreator
        self.formatter = editwin.fregion#idlelib.format.FormatRegion
##        self.flist = editwin.flist#idlelib.pyshell.PyShellFileList
        self.files = editwin.io#idlelib.iomenu.IOBinding

        self.pylint_file = os.path.expanduser(
            os.path.join(idleConf.userdir, 'pylint-out.json'))

##        self.text.bind('<<lint-check>>', self.lint_check_event)
##        self.text.bind('<<lint-remove-comments>>', self.remove_lint_comments_event)
        for attrname in (a for a in dir(self) if not a.startswith('_')):
            if attrname.endswith('_event'):
                bind_name = '-'.join(attrname.split('_')[:-1]).lower()
                self.text.bind(f'<<{bind_name}>>', getattr(self, attrname))
##                print(f'{attrname} -> {bind_name}')

    @classmethod
    def ensure_bindings_exist(cls) -> bool:
        "Ensure key bindings exist in user extensions config. Return True if need to save."
        need_save = False
        section = f'{cls.__name__}_cfgBindings'
        if ensure_section_exists(section):
            need_save = True
        if ensure_values_exist_in_section(section, cls.bind_defaults):
            need_save = True
        return need_save

    @classmethod
    def ensure_config_exists(cls) -> bool:
        "Ensure required configuration exists for this extention. Return True if need to save."
        need_save = False
        if ensure_section_exists(cls.__name__):
            need_save = True
        if ensure_values_exist_in_section(cls.__name__, cls.values):
            need_save = True
        return need_save

    @classmethod
    def reload(cls) -> None:
        "Load class variables from config."
##        # Ensure file default values exist so they appear in settings menu
##        save = cls.ensure_config_exists()
##        if cls.ensure_bindings_exist() or save:
##            idleConf.SaveUserCfgFiles()
        # For all possible config values
        for key, default in cls.values.items():
            # Set attribute of key name to key value from config file
            if not key in {'enable', 'enable_editor', 'enable_shell'}:
                value = idleConf.GetOption('extensions',
                                           cls.__name__,
                                           key,
                                           default=default)
                setattr(cls, key, value)

    def get_msg_line(self, indent: int, msg: str) -> str:
        "Return message line given indent and message."
        strindent = ' '*indent
        return f'{strindent}{self.comment}{msg}'

    def comment_exists(self, line: int, text: str) -> bool:
        "Return True if comment for message already exists."
        self.editwin.gotoline(line-1)
        chars = self.formatter.get_region()[2]
        return self.get_msg_line(0, text) in chars

    def add_comment(self, message: dict, max_exist_up: int=0) -> bool:
        "Return True if added new comment, False if already exists."
        # Get line and message from mypy output
##        file = message['file']
        line = message['line']
        msg = message['message']

        # If there is already a mypy from us comment there, ignore that line.
        # +1-1 is so at least up by 1 is checked, range(0) = []
        for i in range(max_exist_up+1):
            if self.comment_exists(line-(i-1), msg):
                return False

        # Go to line mypy is talking about
        self.editwin.gotoline(line)
##        self.flist.gotofileline(file, line)
        # Get format region
        head, tail, chars, lines = self.formatter.get_region()
        # Figure out line indent
        indent = get_line_indent(lines[0])
        # Add comment line
        lines = [self.get_msg_line(indent, msg)] + lines
        # Save changes
        self.formatter.set_region(head, tail, chars, lines)
        return True

    def add_comments(self, target_filename: str, lint_json: list) -> list[int]:
        "Add comments for each line given in lint_json, from bottom to top."
        files: dict[str, list[dict[str, Any]]] = {}
        start_line = self.editwin.getlineno()
        for comment in lint_json:
            # Make sure used attributes exist (always should)
            for attr in ('line', 'column', 'path', 'message-id', 'message'):
                if not attr in comment:
                    break
            else:# If did not exit prematurely (by break)
                filename = os.path.abspath(comment['path'])
                message = {
                    'file': filename,
                    'line': comment['line'],
                    'column': comment['column'],
                    'message': f"{comment['symbol']} "\
                    f"({comment['message-id']}): {comment['message']}"
                }

                if not filename in files:
                    files[filename] = []
                files[filename].append(message)

        # Only handling messages for target filename
        line_data: dict[int, list] = {}
        if target_filename in files:
            for message in files[target_filename]:
                line: int = message['line']
                if not line in line_data:
                    line_data[line] = []
                line_data[line].append(message)

        line_order = tuple(sorted(line_data, reverse=True))
        first = line_order[-1] if line_order else start_line

        for filename in {f for f in files if f != target_filename}:
            line_data[first].append({
                'file': target_filename,
                'line': first,
                'column': 0,
                'message': f'Another file has errors: {filename}'
            })

        comments = []
        for line in line_order:
            total = len(line_data[line])
            for message in sorted(line_data[line], key=lambda m: m['column']):
                if self.add_comment(message, total):
                    comments.append(line)
        return comments

    def ask_save_dialog(self) -> bool:
        "Ask to save dialog stolen from idlelib.runscript.ScriptBinding"
        msg = 'Source Must Be Saved\n' + 5*' ' + 'OK to Save?'
        confirm = messagebox.askokcancel(
            title='Save Before Run or Check',
            message=msg,
            default=messagebox.OK,
            parent=self.text
        )
        if confirm:
            self.files.save(None)
        return confirm

    @undo_block
    def lint_check_event(self, _) -> str:
        "Preform a pylint check and add comments."
        self.reload()

        # Get file we are checking
        file = os.path.abspath(self.files.filename)

        # Remember where we started
        start_line_no = self.editwin.getlineno()

        if not _HAS_LINT:
            add = 0
            if self.add_comment({
                'file': file,
                'line': start_line_no,
                'message': 'Could not import pylint. '\
                'Please install pylint to use this extension.'
            }, start_line_no):
                add += 1
            self.editwin.gotoline(start_line_no+add)

            # Make bell sound so user knows they need to pay attention
            self.text.bell()
            return 'break'

        # Make sure file is saved.
        if not self.files.get_saved():
            if not self.ask_save_dialog():
                # If not saved, do not run. Would break file.
                self.text.bell()
                return 'break'

        # Get arguments
        try:
            jobs = int(self.jobs)
        except ValueError:
            jobs = 0
        jobs = max(0, jobs)
        args = [file, f'--output={self.pylint_file}',
                '--output-format=json', f'--jobs={jobs}']
        if self.ignore and self.ignore != 'None':
            if ';' not in self.ignore:
                ignore = [self.ignore]
            else:
                ignore = self.ignore.split(';')
            args.append('--disable='+','.join(ignore))

        # Run pylint on open file
        pylint.lint.run.Run(args, exit=False)

        # Read data from temporary file as json
        data = []
        with open(self.pylint_file, 'r', encoding='utf-8') as results:
            data = json.load(results)
            results.close()

        # Add code comments
        lines = self.add_comments(file, data)

        # Return to where we started but offset by added lines
        add = 0
        for line in lines:
            if line < start_line_no:
                add += 1
        self.editwin.gotoline(start_line_no+add)

        # Make bell sound so user knows we are done,
        # as it freezes a bit while pylint looks at the file
        self.text.bell()
        return 'break'

    def remove_lint_comments_event(self, _) -> str:
        "Remove all pylint comments."
        # Get selected region lines
        head, tail, chars, lines = self.formatter.get_region()
        if not self.comment in chars:
            # Make bell sound so user knows this ran even though
            # nothing happened.
            self.text.bell()
            return 'break'
        # Using dict so we can reverse and enumerate
        ldict = dict(enumerate(lines))
        for idx in sorted(ldict.keys(), reverse=True):
            line = ldict[idx]
            # Get line indent, see if after indent there is mypy comment
            indent = get_line_indent(line)
            if line[indent:].startswith(self.comment):
                # If so, remove line
                del lines[idx]
        # Apply changes
        self.formatter.set_region(head, tail, chars, lines)
        return 'break'

    def find_next_lint_comment_event(self, _) -> str:
        "Find next comment."
        self.reload()

        # Get dialog singleton (slighty sketchy, but no other public way)
        search_dialog = search._setup(self.text)# pylint: disable=protected-access

        # Get current search params
        prev_text = search_dialog.engine.getpat()
        prev_regx = search_dialog.engine.isre()
        prev_case = search_dialog.engine.iscase()
        prev_wrap = search_dialog.engine.iswrap()
        prev_back = search_dialog.engine.isback()
        # Set search pattern to comment starter
        pattern = f'\s*{self.comment}'# pylint: disable=anomalous-backslash-in-string
        search_dialog.engine.setcookedpat(pattern)
        search_dialog.engine.revar.set(True)
        search_dialog.engine.casevar.set(True)
        search_dialog.engine.wrapvar.set(self.search_wrap == 'True')
        search_dialog.engine.backvar.set(False)
        # Find current pattern
        search_dialog.find_again(self.text)
        # Re-apply previous search params
        search_dialog.engine.setpat(prev_text)
        search_dialog.engine.revar.set(prev_regx)
        search_dialog.engine.casevar.set(prev_case)
        search_dialog.engine.wrapvar.set(prev_wrap)
        search_dialog.engine.backvar.set(prev_back)
        return 'break'

lintcheck.reload()

if __name__ == '__main__':
    print(f'{__title__} v{__version__}\nProgrammed by {__author__}.\n')
    check_installed()
