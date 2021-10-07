# LintCheck
Python IDLE extension to preform pylint analysis on an open file

## Installation
1) Download this repository and unarchive folder
2) Go to terminal and install with `pip install path/to/LintCheck`.
3) Ensure IDLE is closed or configuration file modifications will be
reverted when you close IDLE in the future.
4) Run command `lintcheck`. It may ask you permission to create new
files and directories. When it's done, you should see the following
output: `Config should be good!`. If attempting to run command
results in error, restart from the beginning. This command will go to
`~/.idlerc/` and edit or create `config-extensions.cfg` and add
a section `[lintcheck]` and add `enable = True` if section does
not exist. LintCheck itself will add more options later.
5) Open IDLE, go to `Options` -> `Configure IDLE` -> `Extensions`.
If everything went well, alongside `ZzDummy` there should be and
option called `lintcheck`. This is where you can configure how
lintcheck works.
6) If step 5 did not work and you cannot see `lintcheck` with `ZzDummy`,
but step 4 worked correctly, then it means [bpo-45357](https://github.com/python/cpython/pull/28713)
has not been accepted or it has but your copy of IDLE is out of date.
Go to section `Patching IDLE`.

### Patching IDLE
1) Create backups of files we will be patching. Linux/macos:
`cd /usr/lib/python3.X` Change to version of python you are using

`cd idlelib; sudo mv config.py config.bak; sudo mv configdialog.py configdialog.bak`

2) Go to the `patch` folder in your terminal. Linux/macos:
`cd /path/to/patch`

3) Copy patched files to system folder. Linux/macos:
Again, replace 3.X with version of python you are using

`sudo cp config.py /usr/lib/python3.X/idlelib/config.py`
`sudo cp configdialog.py /usr/lib/python3.X/idlelib/configdialog.py`

### Information on options
Option `ignore` is a list of pylint messages,
seperated by semicolons (;) that should be disabled using `--disable`.
See `pylint --help` for more information.

Option `jobs` is the number of processes pylint should use when
checking your code, using `--jobs`. See `pylint --help` for more information.
