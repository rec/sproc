"""
##################################################
⛏️subprocessor: subprocesseses for subhumanses  ⛏
##################################################

Run a command in a subprocess and yield lines of text from stdout and stderr

*********
EXAMPLES
*********

.. code-block:: python

    import subprocessor as sub

    CMD = 'my-unix-command "My Cool File.txt" No-file.txt'

    for ok, line in sub.Sub(CMD) as sp:
        if ok:
             print(' ', line)
        else:
             print('!', line)

    if sp.returncode:
        print('Error code', sp.returncode)

    # Return two lists of text lines and a returncode
    out_lines, err_lines, returncode = sub.run(CMD)

    # Call callback functions with lines of text read from stdout and stderr
    returncode = sub.call(CMD, save_results, print_errors)

    # Log stdout and stderr, with prefixes
    returncode = sub.log(CMD)
"""

from queue import Queue
from threading import Thread
import subprocess
import functools
import shlex

__version__ = '1.0.0'
__all__ = ('Sub', 'call', 'run', 'log')


class Sub:
    """
    Iterate over lines of text from a subprocess.

    If `kwargs['shell']` is true, `Popen` expects a string,
    and so if `cmd` is not a string, it is joined using `shlex`.

    If `kwargs['shell']` is false, `Popen` expects a list of strings,
    and so if `cmd` is a string, it is split using `shlex`.
    """

    @functools.wraps(subprocess.Popen)
    def __init__(self, cmd, **kwargs):
        if 'stdout' in kwargs or 'stderr' in kwargs:
            raise ValueError('Cannot set stdout or stderr')

        PIPE = subprocess.PIPE

        self.cmd = cmd
        self.kwargs = dict(kwargs, stderr=PIPE, stdout=PIPE)

        shell = kwargs.get('shell')
        is_str = isinstance(cmd, str)

        if is_str and not shell:
            self.cmd = shlex.split(cmd)
        if not is_str and shell:
            self.cmd = shlex.join(cmd)

        self.returncode = None

    def __iter__(self):
        """
        Yields a sequence of `ok, line` pairs from `stdout` and `stderr` of
        a subprocess, where `ok` is `True` if `line` came from `stdout`
        and `False` if it came from `stderr`.

        After iteration is done, the `.returncode` property contains
        the error code from the subprocess, an integer where 0 means no error.
        """
        queue = Queue()

        def read_stream(ok):
            try:
                stream = self.proc.stdout if ok else self.proc.stderr
                line = '.'
                while line or self.proc.poll() is None:
                    line = stream.readline()
                    if line:
                        queue.put((ok, line))
            finally:
                queue.put((ok, None))

        with subprocess.Popen(self.cmd, **self.kwargs) as self.proc:
            for ok in False, True:
                Thread(target=read_stream, args=(ok,), daemon=True).start()

            finished = 0
            while finished < 2:
                ok, line = queue.get()
                if line:
                    yield ok, line.decode('utf8')
                else:
                    finished += 1

        self.returncode = self.proc.returncode

    def call(self, out=None, err=None):
        """
        Run the subprocess and call function `out` with lines from
        `stdout` and function `err` with lines from `stderr`.

        Blocks until the subprocess is complete: the callbacks are on
        the current thread.
        """
        for ok, line in self:
            out and out(line) if ok else err and err(line)

        return self.returncode

    def run(self):
        """
        Reads lines from `stdout` and `stderr` into two lists `out` and `err`,
        then returns a tuple `(out, err, returncode)`
        """
        out, err = [], []
        self.call(out.append, err.append)
        return out, err, self.returncode

    def log(self, out='  ', err='! ', print=print):
        """
        Read lines from `stdin` and `stderr` and prints them with prefixes

        Returns the shell integer error code from the subprocess, where 0 means
        no error.
        """
        return self.call(lambda x: print(out + x), lambda x: print(err + x))


def call(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).call(out, err)


def run(cmd, **kwds):
    return Sub(cmd, **kwds).run()


def log(cmd, out='  ', err='! ', print=print, **kwds):
    return Sub(cmd, **kwds).log(out, err, print)


_ARG = """
ARGUMENTS"""
_CMD = """
  cmd:
    The command to run in a subprocess: a string or a list or tuple of strings
"""
_KW = """
  kwargs:
    Keyword arguments passed to subprocess.Popen()
"""
_CALL_OUT = """
  out:
    if not None, `out` is called for each line from the subprocess's stdout
"""
_CALL_ERR = """
  err:
    if not None, `err` is called for each line from the subprocess's stderr,
"""
_LOG_OUT = """
  out:
    Prefix for printing lines from stdout
"""
_LOG_ERR = """
  err:
    Prefix for printing lines from stderr
"""
_PRINT = """
  print:
    a function that accepts individual strings
"""


def _unindent(s, offset=8):
    return '\n'.join(i[offset:] for i in s.__doc__.splitlines())


Sub.__doc__ = _unindent(Sub, 4) + _ARG + _CMD + _KW

call.__doc__ = _unindent(Sub.call) + _ARG + _CMD + _CALL_OUT + _CALL_ERR + _KW
run.__doc__ = _unindent(Sub.run) + _ARG + _CMD + _KW
log.__doc__ = _unindent(Sub.log) + _ARG + _CMD + _LOG_OUT + _LOG_ERR + _KW

Sub.call.__doc__ = _unindent(Sub.call) + _ARG + _CALL_OUT + _CALL_ERR
Sub.run.__doc__ = _unindent(Sub.run)
Sub.log.__doc__ = _unindent(Sub.log) + _ARG + _LOG_OUT + _LOG_ERR
