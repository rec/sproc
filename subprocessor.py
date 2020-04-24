"""
⛏️subprocessor: subprocesses for subhumanses  ⛏
===================================================

Run a command in a subprocess and yield lines from stdout and stderr.

EXAMPLES

.. code-block:: python
    import subprocessor as sp

    sub = sp.Sub('ls "My File.txt" foo.txt')
    for is_err, line in sub:
        if is_err:
             print(
        else:
             # Handle stdout here

    if sub.returncode:
        sys.exit(sub.returncode)
"""

import shlex
import subprocess

__version__ = '0.9.1'
__all__ = ('Sub',)


class Sub:
    def __init__(self, cmd, shell=False, **kwargs):
        """
        Construct a subprocessor

        ARGUMENTS
            cmd:
                A list or tuple of strings or a string to run in a subprocess.

                If shell=True, Popen expects a string, so if ``cmd`` is a list,
                it is joined using shlex.

                If shell=False, Popen expects a list of strings, so if ``cmd``
                is a string, it is split using shlex.

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
        self.stderr_first = True

    @property
    def returncode(self):
        return self.proc and self.proc.returncode

    def __iter__(self):
        """
        Iterate over ``is_err, line`` pairs from stdout and stderr of
        the subprocess.

        Iterating starts the subprocess, and reads lines from both stdout and
        stderr, yielding a series of ``is_err, line`` pairs, where ``is_err``
        is true if ``line`` came from stderr.

        After the iterator is done, ``.returncode`` contains the shell integer
        error code from the subprocess, where 0 means no error.
        """
        with subprocess.Popen(self.cmd, **self.kwargs) as self.proc:
            data_received = True

            while data_received:
                data_received = False

                for first in True, False:
                    is_err = first == self.stderr_first
                    stream = self.proc.stderr if is_err else self.proc.stdout

                    while True:
                        line = stream.readline()
                        if not line:
                            break

                        data_received = True
                        yield is_err, line.decode('utf-8')

                data_received = self.proc.poll() is None or data_received

    def call(self, out=None, err=None):
        """
        Run a subprocess, read lines from its stdin and stderr, and send them
        to callbacks.

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
        for is_err, line in self:
            if is_err:
                err and err(line)
            else:
                out and out(line)
        return self.returncode

    def run(self):
        """
        Starts a subprocess ``p``, reads lines from stdout and stderr into two
        arrays ``out`` and ``err``, then returns a triple:
            ``out, err, p.returncode``
        """
        out, err = [], []
        error_code = self.call(out.append, err.append)
        return out, err, error_code

    def log(self, out='  ', err='* ', print=print):
        """
        Runs a command as a  subprocess, reads lines from stdin and stderr, and
        prints them.

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
