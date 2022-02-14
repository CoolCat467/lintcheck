#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Lint Check - Use pylint to check open file, then add comments to file.

"Lint Check Extension"

# Programmed by CoolCat467

__title__ = 'lintcheck'
__author__ = 'CoolCat467'
__license__ = 'GPLv3'
__version__ = '0.1.1'
__ver_major__ = 0
__ver_minor__ = 1
__ver_patch__ = 1

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
        module = __import__(__title__)
        # Get extension class
        if hasattr(module, __title__):
            cls = getattr(module, __title__)
            # Get extension class keybinding defaults
            add_data = ''
            if hasattr(cls, 'values'):
                # Get config defaults
                values = [f'{key} = {default}' for key, default in cls.values.items()]
                values = '\n'.join(values)
                # Add to add_data
                add_data += f"\n[{__title__}]\n{values}"
            if hasattr(cls, 'bind_defaults'):
                # Get keybindings data
                values = [f'{event} = {key}' for event, key in cls.bind_defaults.items()]
                values = '\n'.join(values)
                # Add to add_data
                add_data += f"\n[{__title__}_cfgBindings]\n{values}"
        # Make sure linebreaks will go properly in terminal
        add_data = add_data.replace('\n', '\\n')
        # Tell them command
        print(f"echo -e '{add_data}' | sudo tee -a {ex_defaults}")
        print()
    else:
        print('Config should be good!')
        return True
    return False

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

class lintcheck:# pylint: disable=C0103
    "Add comments from pylint to an open program."
    # Extend the file and format menus.
    menudefs = [
        ('file', [
            ('_Lint Check File', '<<lint-check>>')
        ] ),
        ('format', [
            ('R_emove Lint Comments', '<<lint-remove-comments>>')
        ] )
    ]
    # Default values for config file
    values = {'enable': 'True',
              'enable_editor': 'True',
              'enable_shell': 'False',
              'ignore': 'None',
              'jobs': '0'}
    # Default keybinds for config file
    bind_defaults = {'lint-check': '<Control-Shift-Key-C>',
                     'lint-remove-comments': '<Control-Alt-Key-c>'}
    comment = '# lintcheck: '

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
            os.path.join(idleConf.userdir, 'pylint-out.json'))

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
##        # Ensure file default values exist so they appear in settings menu
##        save = cls.ensure_config_exists()
##        if cls.ensure_bindings_exist() or save:
##            idleConf.SaveUserCfgFiles()
        # For all possible config values
        for key in cls.values:
            # Set attribute of key name to key value from config file
            if not key in {'enable', 'enable_editor', 'enable_shell'}:
                value = idleConf.GetOption('extensions', cls.__name__, key)
                setattr(cls, key, value)

    def add_comment(self, message):
        "Add pylint comments."
        # Get line, message id, and message from pylint output
        line = message['line']
        msg_id = message['message-id']
        symbol = message['symbol']
        msg = message['message']

        # Go to line pylint is talking about
        self.editwin.gotoline(line)
##        self.flist.gotofileline(file, line-1)
        # Get format region
        head, tail, chars, lines = self.formatter.get_region()
        # If there is already a pylint from us comment there, ignore that line.
        if self.comment in chars:
            return
        # Figure out line indent
        indent = get_line_indent(lines[0])
        # Add comment line
        lines = [' '*indent+self.comment+symbol+' ('+msg_id+'): '+msg] + lines
        # Save changes
        self.formatter.set_region(head, tail, chars, lines)

    def add_comments(self, filename: str, lint_json: list) -> None:
        "Add comments for each line given in lint_json, from bottom to top."
        # Get messages seperated by what line they are on
        lines = {}
        for msg in lint_json:
            # Make sure used attributes exist (always should)
            skip = False
            for attr in ('line', 'column', 'path', 'message-id', 'message'):
                if not attr in msg:
                    skip = True
                    break
            if skip:
                continue
            # If error not in open file, don't try to edit this one for it.
            if os.path.abspath(msg['path']) != filename:
                continue
            # Make lines go {lineno}: [msg1, msg2, msg3, ...]
            if not msg['line'] in lines:
                lines[msg['line']] = [msg]
                continue
            lines[msg['line']].append(msg)
        # Sort out lines so last line commented first so invalid positions commented
        for key in sorted(lines.keys(), reverse=True):
            # Sort messages per line by column
            for msg in sorted(lines[key], key=lambda m: m['column']):
                # Add comment for each message
                self.add_comment(msg)

    @undo_block
    def lint_check_event(self, _) -> None:
        "Preform a pylint check and add comments."
        self.reload()
        if not _HAS_LINT:
            head, tail, chars, lines = self.formatter.get_region()
            lines[-1] = (self.comment+'Could not import pylint. '\
                         'Please install pylint to use this extension.')
            lines.append('')
            self.formatter.set_region(head, tail, chars, lines)
            # Make bell sound so user knows they need to pay attension
            self.text.bell()
            return
        # Make sure file is saved.
        self.files.maybesave()
        # If not saved, do not run. Would break file.
        if not self.files.get_saved():
            self.text.bell()
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
        self.add_comments(file, data)
        
##        # Remove file
##        os.remove(self.pylint_file)
        
        # Make bell sound so user knows we are done,
        # as it freezes a bit while pylint looks at the file
        self.text.bell()

    def remove_lint_comments_event(self, _) -> None:
        "Remove all pylint comments."
        # Get selected region lines
        head, tail, chars, lines = self.formatter.get_region()
        if not self.comment in chars:
            # Make bell sound so user knows this ran even though
            # nothing happened.
            self.text.bell()
            return
        # Using dict so we can reverse and enumerate
        ldict = dict(enumerate(lines))
        for idx in sorted(ldict.keys(), reverse=True):
            line = ldict[idx]
            # Get line indent, see if after indent there is pylint comment
            indent = get_line_indent(line)
            if line[indent:].startswith(self.comment):
                # If so, remove line
                del lines[idx]
        # Apply changes
        self.formatter.set_region(head, tail, chars, lines)

lintcheck.reload()

if __name__ == '__main__':
    print(f'{__title__} v{__version__}\nProgrammed by {__author__}.\n')
    check_installed()
