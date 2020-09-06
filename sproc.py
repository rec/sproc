"""
##################################################
⛏️sproc: subprocesseses for subhumanses  ⛏
##################################################

Run a command in a subprocess and yield lines of text from stdout and stderr

*********
EXAMPLES
*********

.. code-block:: python

    import sproc

    CMD = 'my-unix-command "My Cool File.txt" No-file.txt'

    for ok, line in sproc.Sub(CMD) as sp:
        if ok:
             print(' ', line)
        else:
             print('!', line)

    if sp.returncode:
        print('Error code', sp.returncode)

    # Return two lists of text lines and a returncode
    out_lines, err_lines, returncode = sproc.run(CMD)

    # Call callback functions with lines of text read from stdout and stderr
    returncode = sproc.call(CMD, save_results, print_errors)

    # Log stdout and stderr, with prefixes
    returncode = sproc.log(CMD)
"""

from queue import Queue
from threading import Thread
import functools
import shlex
import subprocess

__version__ = '2.0.2'
__all__ = ('Sub', 'call', 'call_async', 'run', 'log')

DEFAULTS = {'stderr': subprocess.PIPE, 'stdout': subprocess.PIPE}


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

        self.cmd = cmd
        self.kwargs = dict(kwargs, **DEFAULTS)
        self._threads = []

        shell = kwargs.get('shell')
        is_str = isinstance(cmd, str)

        if is_str and not shell:
            self.cmd = shlex.split(cmd)
        if not is_str and shell:
            self.cmd = shlex.join(cmd)

    @property
    def returncode(self):
        return self.proc and self.proc.returncode

    def __iter__(self):
        """
        Yields a sequence of `ok, line` pairs from `stdout` and `stderr` of
        a subprocess, where `ok` is `True` if `line` came from `stdout`
        and `False` if it came from `stderr`.

        After iteration is done, the `.returncode` property contains
        the error code from the subprocess, an integer where 0 means no error.
        """
        queue = Queue()

        with subprocess.Popen(self.cmd, **self.kwargs) as self.proc:
            for ok in False, True:
                self._start_thread(ok, lambda o, s: queue.put((o, s)))

            finished = 0
            while finished < 2:
                ok, line = queue.get()
                if line:
                    yield ok, line
                else:
                    finished += 1

    def call(self, out=None, err=None):
        """
        Run the subprocess, and call function `out` with lines from
        `stdout` and function `err` with lines from `stderr`.

        Blocks until the subprocess is complete: the callbacks to `out` and
        'err` are on the current thread.
        """
        callback = self._callback(out, err)
        for ok, line in self:
            callback(ok, line)

        return self.returncode

    def call_async(self, out=None, err=None):
        """
        Run the subprocess, and asynchronously call function `out` with lines
        from `stdout`, and function `err` with lines from `stderr`.

        Does not block - immediately returns.
        """
        with subprocess.Popen(self.cmd, **self.kwargs) as self.proc:
            callback = self._callback(out, err)
            for ok in False, True:
                self._start_thread(ok, callback)

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

    def join(self, timeout=None):
        """Join the stream handling threads"""
        for t in self._threads:
            t.join(timeout)

    def kill(self):
        """Kill the running process, if any"""
        self.proc and self.proc.kill()

    def _start_thread(self, ok, callback):
        def read_stream():
            try:
                stream = self.proc.stdout if ok else self.proc.stderr
                line = '.'
                while line or self.proc.poll() is None:
                    line = stream.readline()
                    if line:
                        callback(ok, line.decode('utf8'))
            finally:
                callback(ok, None)

        th = Thread(target=read_stream, daemon=True)
        th.start()
        self._threads.append(th)

    def _callback(self, out, err):
        if out and err:
            return lambda ok, line: line and (out(line) if ok else err(line))
        if out:
            return lambda ok, line: line and ok and out(line)
        if err:
            return lambda ok, line: line and not ok and err(line)
        else:
            return lambda ok, line: None


def call(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).call(out, err)


def call_async(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).call_async(out, err)


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
Sub.call.__doc__ = _unindent(Sub.call) + _ARG + _CALL_OUT + _CALL_ERR

call_async.__doc__ = _unindent(Sub.call_async) + (
    _ARG + _CMD + _CALL_OUT + _CALL_ERR + _KW
)
Sub.call_async.__doc__ = _unindent(Sub.call_async) + (
    _ARG + _CALL_OUT + _CALL_ERR
)

run.__doc__ = _unindent(Sub.run) + _ARG + _CMD + _KW
Sub.run.__doc__ = _unindent(Sub.run)

log.__doc__ = _unindent(Sub.log) + _ARG + _CMD + _LOG_OUT + _LOG_ERR + _KW
Sub.log.__doc__ = _unindent(Sub.log) + (_ARG + _LOG_OUT + _LOG_ERR)
