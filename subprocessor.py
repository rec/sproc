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

import shlex
import subprocess

__version__ = '0.9.1'
__all__ = ('Sub',)


class Sub:
    def __init__(self, cmd, shell=False, **kwargs):
        """
        An iterator over ``ok, line`` pairs from stdout and stderr of
        the subprocess.

        Iterating starts the subprocess, and reads lines from both stdout and
        stderr, yielding a sequence of ``ok, line`` pairs, where ``ok``
        is true if ``line`` came from stdout and false if it came from stderr.

        After the iterator is done, the ``.returncode`` property contains
        the error code from the subprocess, an integer where 0 means no error.

        ARGUMENTS
            cmd:
                A list or tuple of strings or a string to run in a subprocess.

            shell:
                If shell is true, the specified command will be executed
                through the shell (passed to subprocess.Popen()).

                If shell is true, Popen expects a string,
                and so if ``cmd`` is a list, it is joined using shlex.

                If shell is false, Popen expects a list of strings,
                and so if ``cmd`` is a string, it is split using shlex.

            kwargs:
                Keyword arguments passed to subprocess.Popen()
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
        self.stdout_first = False

    @property
    def returncode(self):
        return self.proc and self.proc.returncode

    def __iter__(self):
        with subprocess.Popen(self.cmd, **self.kwargs) as self.proc:
            data_received = True

            while data_received:
                data_received = False

                for first in True, False:
                    is_out = first == self.stdout_first
                    stream = self.proc.stdout if is_out else self.proc.stderr

                    while True:
                        line = stream.readline()
                        if not line:
                            break

                        data_received = True
                        yield is_out, line.decode('utf-8')

                data_received = self.proc.poll() is None or data_received

    def call(self, out=None, err=None):
        """
        Read lines from stdin and stderr and send them to callbacks

        Returns the shell integer error code from the subprocess, where 0 means
        no error.

        ARGUMENTS
            out:
              ``out`` is called for each line from the subprocess's stdout,
              if not None.

            err:
              ``err`` is called for each line from the subprocess's stderr,
              if not None.
        """
        for ok, line in self:
            ok and out and out(line)
            not ok and err and err(line)

        return self.returncode

    def run(self):
        """
        Reads lines from stdout and stderr into two arrays ``out`` and ``err``,
        then returns a triple ``out, err, returncode``.
        """
        out, err = [], []
        error_code = self.call(out.append, err.append)
        return out, err, error_code

    def log(self, out='  ', err='* ', print=print):
        """
        Read lines from stdin and stderr and prints them with prefixes

        Returns the shell integer error code from the subprocess, where 0 means
        no error.

        ARGUMENTS
            out:
                Prefix for each line to stdout

            err:
                Prefix for each line to stderr

            print:
                a function that accepts individual strings
        """
        return self.call(
            out=lambda x: print(out + x), err=lambda x: print(err + x)
        )


def call(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).call(out, err)


def run(cmd, out=None, err=None, **kwds):
    return Sub(cmd, **kwds).run()


def log(cmd, out='  ', err='* ', print=print, **kwds):
    return Sub(cmd, **kwds).log(out, err, print)
