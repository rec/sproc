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
import subprocess

__version__ = '0.9.1'
__all__ = ('Sub',)


class Sub:
    def __init__(self, cmd, shell=False, **kwargs):
        """
        A subprocess that can iterate iterate over lines

        Yields a sequence of ``ok, line`` pairs from stdout and stderr of
        a subprocess, where ``ok`` is true if ``line`` came from stdout
        and false if it came from stderr.

        After iteration is done, the ``.returncode`` property contains
        the error code from the subprocess, an integer where 0 means no error.
        """
        if 'stdout' in kwargs or 'stderr' in kwargs:
            raise ValueError('Cannot set stdout or stderr')
        self.kwargs = dict(
            kwargs, shell=shell, stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )

        self.cmd = cmd
        if isinstance(cmd, str):
            if not shell:
                self.cmd = shlex.split(cmd)
        else:
            if shell:
                self.cmd = shlex.join(cmd)

        self.proc = None

    @property
    def returncode(self):
        """
        Returns the shell integer error code from the subprocess, where
        0 means no error, or None if the subprocess has not yet completed.
        """
        return self.proc and self.proc.returncode

    def __iter__(self):
        queue = Queue()

        def service_stream(ok):
            stream = self.proc.stdout if ok else self.proc.stderr
            line = '.'
            while line or self.proc.poll() is None:
                line = stream.readline()
                if line:
                    queue.put((ok, line))
            queue.put((ok, None))

        with subprocess.Popen(self.cmd, **self.kwargs) as self.proc:
            for ok in False, True:
                Thread(target=service_stream, args=(ok,), daemon=True).start()

            nulls = 0
            while nulls < 2:
                ok, line = queue.get()
                if line:
                    yield ok, line.decode('utf8')
                else:
                    nulls += 1

    def callback(self, out=None, err=None):
        """
        Run the subprocess and call optional function ``out`` with lines from
        ``stdout`` and optional ``err`` with lines from ``stderr``.

        """
        for ok, line in self:
            (out and out(line)) if ok else (err and err(line))

        return self.returncode

    def run(self):
        """
        Reads lines from stdout and stderr into two arrays ``out`` and ``err``,
        then returns a triple ``out, err, returncode``.
        """
        out, err = [], []
        error_code = self.callback(out.append, err.append)
        return out, err, error_code

    def log(self, out='  ', err='* ', print=print):
        """
        Read lines from stdin and stderr and prints them with prefixes

        Returns the shell integer error code from the subprocess, where 0 means
        no error.
        """
        return self.callback(
            out=lambda x: print(out + x), err=lambda x: print(err + x)
        )


def callback(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).callback(out, err)


def run(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).run()


def log(cmd, out='  ', err='* ', print=print, **kwds):
    return Sub(cmd, **kwds).log(out, err, print)


_DOC_CMD = """
    cmd:
        A list or tuple of strings or a string to run in a subprocess.
"""
_DOC_SHELL = """
    shell:
        If shell is true, the specified command will be executed
        through the shell (passed to subprocess.Popen()).

        If shell is true, Popen expects a string,
        and so if ``cmd`` is a list, it is joined using shlex.

        If shell is false, Popen expects a list of strings,
        and so if ``cmd`` is a string, it is split using shlex.
"""
_DOC_KWARGS = """
    kwargs:
        Keyword arguments passed to subprocess.Popen()
"""
_DOC_CALL_OUT = """
    out:
      ``out`` is called for each line from the subprocess's stdout,
      if not None.
"""
_DOC_CALL_ERR = """
    err:
      ``err`` is called for each line from the subprocess's stderr,
      if not None.
"""
_DOC_LOG_OUT = """
    out:
        Prefix for each line to stdout
"""
_DOC_LOG_ERR = """
    err:
        Prefix for each line to stderr
"""
_DOC_PRINT = """
    print:
        a function that accepts individual strings
"""
