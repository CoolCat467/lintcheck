#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Lint Check - Use pylint to check open file, then add comments to file.

"""Lint Check"""

# Programmed by CoolCat467

__title__ = 'LintCheck'
__author__ = 'CoolCat467'
__version__ = '0.0.0'
__ver_major__ = 0
__ver_minor__ = 0
__ver_patch__ = 0

import os
import json
from functools import wraps

from idlelib.config import idleConf

_HAS_LINT = True
try:
    import pylint.lint.run
except ImportError:
    print(f'{__file__}: Pylint not installed!')
    _HAS_LINT = False

##def format_selection(format_line):
##    "Apply a formatting function to all of the selected lines."
##
##    @wraps(format_line)
##    def apply(self, event=None):
##        head, tail, chars, lines = self.formatter.get_region()
##        for pos in range(len(lines) - 1):
##            line = lines[pos]
##            lines[pos] = format_line(self, line)
##        self.formatter.set_region(head, tail, chars, lines)
##        return 'break'
##
##    return apply

def get_line_indent(text:str, char:str=' ') -> int:
    "Return line indent."
    idx = 0
    for idx, cur in enumerate(text.split(char)):
        if cur != '':
            break
    return idx

def ensure_section_exists(section:str) -> bool:
    "Ensure section exists in user extensions config. Return True if created."
    if not section in idleConf.GetSectionList('user', 'extensions'):
        idleConf.userCfg['extensions'].AddSection(section)
        return True
    return False

def undo_block(func):
    "Mark block of edits as a single undo block."
    @wraps(func)
    def undo_wrapper(self, *args, **kwargs):
        "Wrap function in start and stop undo events."
        self.text.undo_block_start()
        value = func(self, *args, **kwargs)
        self.text.undo_block_stop()
        return value
    return undo_wrapper

def ensure_values_exist_in_section(section:str, values:dict) -> bool:
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

class LintCheck:
    """Prepend or remove initial text from selected lines."""

    # Extend the format menu.
    menudefs = [
        ('file', [
            ('_Lint Check File', '<<lint-check>>')
        ] ),
        ('format', [
            ('R_emove Lint Comments', '<<lint-remove-comments>>')
        ] )
    ]
    values = {'enable': 'True',
              'enable_editor': 'True',
              'enable_shell': 'False',
              'ignore': 'C0303',
              'jobs': '0'}
    bind_defaults = {'lint-check': '<Control-Shift-Key-C>',
                     'lint-remove-comments': '<Control-Alt-Key-c>'}
    comment = '# pylint: '

    ignore = ''
    jobs = '0'

    def __init__(self, editwin):
        "Initialize the settings for this extension."
        self.editwin = editwin#idlelib.pyshell.PyShellEditorWindow
        self.text = editwin.text#idlelib.multicall.MultiCallCreator
        self.formatter = editwin.fregion#idlelib.format.FormatRegion
##        self.flist = editwin.flist#idlelib.pyshell.PyShellFileList
        self.files = editwin.io#idlelib.iomenu.IOBinding

        self.pylint_file = os.path.expanduser(
            os.path.join('~', '.idlerc', 'pylint-out.json'))

        self.text.bind('<<lint-check>>', self.lint_check_event)
        self.text.bind('<<lint-remove-comments>>', self.remove_lint_comments_event)

    @classmethod
    def ensure_bindings_exist(cls) -> bool:
        "Ensure key bindings exist in user extensions config. Return True if need to save."
        need_save = False
        section = cls.__name__+'_cfgBindings'
        if ensure_section_exists(section):
            need_save = True
        if ensure_values_exist_in_section(section, cls.bind_defaults):
            need_save = True
        return need_save

    @classmethod
    def ensure_config_exists(cls):
        "Ensure required configuration exists for this extention. Return True if need to save."
        need_save = False
        if ensure_section_exists(cls.__name__):
            need_save = True
        if ensure_values_exist_in_section(cls.__name__, cls.values):
            need_save = True
        return need_save

    @classmethod
    def reload(cls):
        "Load class variables from config."
        save = cls.ensure_config_exists()
        if cls.ensure_bindings_exist() or save:
            idleConf.SaveUserCfgFiles()
        for key in cls.values:
            if not key in {'enable', 'enable_editor', 'enable_shell',
                           'values', 'bind_defaults', 'comment'}:
                value = idleConf.GetOption('extensions', cls.__name__, key)
                setattr(cls, key, value)

    def add_comment(self, message):
        "Add pylint comments."
        line = message['line']
        msg_id = message['message-id']
        msg = message['message']

        self.editwin.gotoline(max(0, line-1))
        #self.flist.gotofileline(file, max(0, line-1))
        head, tail, chars, lines = self.formatter.get_region()
        if self.comment in chars:
            return
        indent_match_idx = len(lines)-2 if len(lines) > 1 else 0
        indent = get_line_indent(lines[indent_match_idx])
        lines[-1] = ' '*indent+self.comment+msg_id+': '+msg
        lines.append('')
        self.formatter.set_region(head, tail, chars, lines)

    def add_comments(self, filename, lint_json):
        "Add comments for each line given in lint_json, from bottom to top."
        # Get messages seperated by what line they are on
        lines = {}
        for msg in lint_json:
            if not 'line' in msg:
                continue
            if not 'path' in msg:
                continue
            if os.path.abspath(msg['path']) != filename:
                continue
            if not msg['line'] in lines:
                lines[msg['line']] = [msg]
                continue
            lines[msg['line']].append(msg)
        # Sort messages per line by column
        by_col = lambda m: m['column']
        for line, messages in lines.items():
            if len(messages) > 1:
                lines[line] = sorted(messages, key=by_col)
        # Sort out lines so last line commented first
        for key in sorted(lines.keys(), reverse=True):
            # Add comment for each message
            for msg in lines[key]:
                self.add_comment(msg)

    @undo_block
    def lint_check_event(self, _):
        "Preform a pylint check and add comments."
        self.reload()
        if not _HAS_LINT:
            head, tail, chars, lines = self.formatter.get_region()
            lines[-1] = (self.comment+'Could not import pylint. '\
                         'Please install pylint to use this extension.')
            lines.append('')
            self.formatter.set_region(head, tail, chars, lines)
            return
        # Make sure file is saved.
        self.files.maybesave()
        # If not saved, do not run. Would break file.
        if not self.files.get_saved():
            return
        # Get arguments
        file = os.path.abspath(self.files.filename)
        try:
            jobs = int(self.jobs)
        except ValueError:
            jobs = 0
        jobs = max(0, jobs)
        args = [file, f'--output={self.pylint_file}',
                '--output-format=json', f'--jobs={jobs}']
        if self.ignore:
            if ';' not in self.ignore:
                ignore = [self.ignore]
            else:
                ignore = self.ignore.split(';')
            args.append('--disable='+','.join(ignore))

        pylint.lint.run.Run(args, exit=False)

        data = []
        with open(self.pylint_file, 'r', encoding='utf-8') as results:
            data = json.load(results)
            results.close()
        os.remove(self.pylint_file)
        self.add_comments(file, data)

    def remove_lint_comments_event(self, _):
        "Remove all pylint comments."
        head, tail, chars, lines = self.formatter.get_region()
        if not self.comment in chars:
            return
        ldict = dict(enumerate(lines))
        for idx in sorted(ldict, reverse=True):
            line = ldict[idx]
            indent = get_line_indent(line)
            if line[indent:].startswith(self.comment):
                del lines[idx]
        self.formatter.set_region(head, tail, chars, lines)

##class _FakeEditWin:
##    "Fake edit window to help debug extention."
##    editwin = None
##    class Txt:
##        "Fake Text class."
##        @staticmethod
##        def bind(name, func):
##            "Fake bind name to function."
##            print(f'event {name} fake bound to {func}')
##        @staticmethod
##        def event_add(event1, event2):
##            "Fake bind event2 to event1."
##            print(f'{event2} fake added to {event1}')
##    text = Txt()
##    fregion = None

LintCheck.reload()

if __name__ == '__main__':
    print(f'{__title__} v{__version__}\nProgrammed by {__author__}.')
