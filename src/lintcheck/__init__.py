#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TITLE DISCRIPTION

"""Lint Check"""

# Programmed by CoolCat467

from checker import lintcheck

import os as _os

def check_installed():
    "Make sure extension installed."
    # Make sure ~/.idlerc folder exists
    path = _os.path.join(_os.path.expanduser('~'), '.idlerc')
    if not _os.path.exists(path):
        last = _os.path.split(path)[1]
        create = input(
            f'Path "{path}" does not exist. Create folder "{last}"? (Y/n) : ').lower() != 'n'
        if not create:
            return
        _os.mkdir(path)
    # Make sure config-extensions.cfg file exists
    path = _os.path.join(path, 'config-extensions.cfg')
    if not _os.path.exists(path):
        last = _os.path.split(path)[1]
        create = input(
            f'Path "{path}" does not exist. Create file "{last}"? (Y/n) : ').lower() != 'n'
        if not create:
            return
    # Get current data
    current_data = ''
    with open(path, mode='r', encoding='utf-8') as config:
        current_data = config.read()
        config.close()
    # If extension does not have section,
    if not '[lintcheck]' in current_data:
        print('Adding lintcheck to enabled extensions config...')
        # Add enable
        with open(path, mode='a', encoding='utf-8') as config:
            config.write('[lintcheck]\nenable = True\n')
            config.close()
    print('Config should be good!')
