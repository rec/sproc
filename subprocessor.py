"""
⛏️subprocessor: subprocesses for subhumanses  ⛏
===================================================

Run a command in a subprocess and yield lines from stdout and stderr.

EXAMPLES

.. code-block:: python
    import subprocessor as sp

    cmd = 'my-unix-command "My File.txt" foo.txt'

    for ok, line in sp.Sub(cmd):
        if ok:
             print('Found', line)
        else:
             print('ERROR', line)
"""
from queue import Queue
from threading import Thread
import shlex
from subprocess import PIPE, Popen

__version__ = '0.9.1'
__all__ = ('Sub', 'call', 'run', 'log')


class Sub:
    """
    A subprocess that can iterate iterate over lines

    Yields a sequence of `ok, line` pairs from `stdout` and `stderr` of
    a subprocess, where `ok` is `True` if `line` came from `stdout`
    and `False` if it came from `stderr`.

    After iteration is done, the `.returncode` property contains
    the error code from the subprocess, an integer where 0 means no error.
    """

    def __init__(self, cmd, **kwargs):
        if 'stdout' in kwargs or 'stderr' in kwargs:
            raise ValueError('Cannot set stdout or stderr')

        self.cmd = cmd
        self.kwargs = dict(kwargs, stderr=PIPE, stdout=PIPE)
        self.proc = None

        shell = kwargs.get('shell')
        is_str = isinstance(cmd, str)

        if is_str and not shell:
            self.cmd = shlex.split(cmd)
        elif not is_str and shell:
            self.cmd = shlex.join(cmd)

    @property
    def returncode(self):
        """
        Returns the shell integer error code from the subprocess, where
        0 means no error, or None if the subprocess has not yet completed.
        """
        return self.proc and self.proc.returncode

    def __iter__(self):
        queue = Queue()

        def target(ok):
            try:
                stream = self.proc.stdout if ok else self.proc.stderr
                line = '.'
                while line or self.proc.poll() is None:
                    line = stream.readline()
                    if line:
                        queue.put((ok, line))
            finally:
                queue.put((ok, None))

        with Popen(self.cmd, **self.kwargs) as self.proc:
            for ok in False, True:
                Thread(target=target, args=(ok,), daemon=True).start()

            finished = 0
            while finished < 2:
                ok, line = queue.get()
                if line:
                    yield ok, line.decode('utf8')
                else:
                    finished += 1

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
        Reads lines from `stdout` and `stderr` into two arrays `out` and `err`,
        then returns a triple `out, err, returncode`.
        """
        out, err = [], []
        error_code = self.call(out.append, err.append)
        return out, err, error_code

    def log(self, out='  ', err='* ', print=print):
        """
        Read lines from `stdin` and `stderr` and prints them with prefixes

        Returns the shell integer error code from the subprocess, where 0 means
        no error.
        """
        return self.call(
            out=lambda x: print(out + x), err=lambda x: print(err + x)
        )


def call(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).call(out, err)


def run(cmd, **kwds):
    return Sub(cmd, **kwds).run()


def log(cmd, out='  ', err='* ', print=print, **kwds):
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
_KW = """
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


def _fix(s, offset=8):
    return '\n'.join(i[offset:] for i in s.__doc__.splitlines()) + _ARG


Sub.__doc__ = _fix(Sub, offset=4) + _CMD + _KW

call.__doc__ = _fix(Sub.call) + _CMD + _CALL_OUT + _CALL_ERR + _KW
run.__doc__ = _fix(Sub.run) + _CMD + _KW
log.__doc__ = _fix(Sub.log) + _CMD + _LOG_OUT + _LOG_ERR + _KW

Sub.call.__doc__ = _fix(Sub.call) + _CALL_OUT + _CALL_ERR
Sub.log.__doc__ = _fix(Sub.log) + _LOG_OUT + _LOG_ERR
