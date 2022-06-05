# LintCheck
Python IDLE extension to preform pylint analysis on an open file

## Installation
1) Go to terminal and install with `pip install lintcheck`.
2) Run command `lintcheck`. You will likely see a message saying
`lintcheck not in system registered extensions!`. Run the command
given to add lintcheck to your system's IDLE extension config file.
3) Again run command `lintcheck`. This time, you should see the following
output: `Config should be good!`.
4) Open IDLE, go to `Options` -> `Configure IDLE` -> `Extensions`.
If everything went well, alongside `ZzDummy` there should be and
option called `lintcheck`. This is where you can configure how
lintcheck works.

### Information on options
Option `ignore` is a list of pylint messages,
seperated by semicolons (;) that should be disabled using `--disable`.
See `pylint --help` for more information.

Option `jobs` is the number of processes pylint should use when
checking your code, using `--jobs`. See `pylint --help` for more information.

Option `search_wrap` is a boolian of whether or not searching for
the next `# lintcheck: ` comment will wrap around or not, defaults to
False.
