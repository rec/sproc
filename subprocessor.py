"""
⛏️subprocessor: subprocesses for subhumanses  ⛏
===================================================

Run a command in a subprocess and yield lines from stdout and stderr.

EXAMPLES

.. code-block:: python

    import subprocessor as sp

    CMD = 'my-unix-command "My File.txt" foo.txt'

    for ok, line in sp.Sub(CMD):
        if ok:
             print('Found', line)
        else:
             print('ERROR', line)

    # Return arrays of lines and a returncode
    stdout, stderr, returncode = sp.run(CMD)

    # Call callback functions with lines of text
    returncode = sp.call(CMD, stdout_callback, stderr_callback)

    # Log stdout and stderr as they come in, with prefixes
    returncode = sp.log(CMD)
"""

from queue import Queue
from threading import Thread
import subprocess
import functools
import shlex

__version__ = '0.9.1'
__all__ = ('Sub', 'call', 'run', 'log')


class Sub:
    """
    Iterate over lines of text from a subprocess.
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

        with subprocess.Popen(self.cmd, **self.kwargs) as proc:

            def read_stream(ok):
                try:
                    stream = proc.stdout if ok else proc.stderr
                    line = '.'
                    while line or proc.poll() is None:
                        line = stream.readline()
                        if line:
                            queue.put((ok, line))
                finally:
                    queue.put((ok, None))

            for ok in False, True:
                Thread(target=read_stream, args=(ok,), daemon=True).start()

            finished = 0
            while finished < 2:
                ok, line = queue.get()
                if line:
                    yield ok, line.decode('utf8')
                else:
                    finished += 1

        self.returncode = proc.returncode

    def call(self, out=None, err=None):
        """
        Run the subprocess and call optional function `out` with lines from
        `stdout` and optional `err` with lines from `stderr`.
        """
        for ok, line in self:
            out and out(line) if ok else err and err(line)

        return self.returncode

    def run(self):
        """
        Reads lines from `stdout` and `stderr` into two arrays of lines
        then returns a triple: `stdout, stderr, returncode'
        """
        out, err = [], []
        for ok, line in self:
            (out if ok else err).append(line)

        return out, err, self.returncode

    def log(self, out='  ', err='! ', print=print):
        """
        Read lines from `stdin` and `stderr` and prints them with prefixes

        Returns the shell integer error code from the subprocess, where 0 means
        no error.
        """
        return self.call(
            out=lambda x: print(out + x), err=lambda x: print(err + x)
        )
        return self.call(
            out=lambda x: print(out + x), err=lambda x: print(err + x)
        )


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
    A list or tuple of strings or a string to run in a subprocess.

    If `kwargs['shell']` is true, `Popen` expects a string,
    and so if `cmd` is not a string, it is joined using `shlex`.

    If `kwargs['shell']` is false, `Popen` expects a list of strings,
    and so if `cmd` is a string, it is split using `shlex`.
"""
_KWARGS = """
  kwargs:
    Keyword arguments passed to subprocess.Popen()
"""
_CALL_OUT = """
  out:
    `out` is called for each line from the subprocess's stdout,
    if not None.
"""
_CALL_ERR = """
  err:
    `err` is called for each line from the subprocess's stderr,
    if not None.
"""
_LOG_OUT = """
  out:
    Prefix for each line to stdout
"""
_LOG_ERR = """
  err:
    Prefix for each line to stderr
"""
_PRINT = """
  print:
    a function that accepts individual strings
"""


def _unindent(s, offset=8):
    return '\n'.join(i[offset:] for i in s.__doc__.splitlines()) + _ARG


Sub.__doc__ = _unindent(Sub, 4) + _CMD + _KWARGS

call.__doc__ = _unindent(Sub.call) + _CMD + _CALL_OUT + _CALL_ERR + _KWARGS
run.__doc__ = _unindent(Sub.run) + _CMD + _KWARGS
log.__doc__ = _unindent(Sub.log) + _CMD + _LOG_OUT + _LOG_ERR + _KWARGS

Sub.call.__doc__ = _unindent(Sub.call) + _CALL_OUT + _CALL_ERR
Sub.log.__doc__ = _unindent(Sub.log) + _LOG_OUT + _LOG_ERR
