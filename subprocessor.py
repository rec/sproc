import shlex
import subprocess

__version__ = '0.9.1'

_SUBPROCESS_KWDS = {
    'shell': False,
    'stderr': subprocess.PIPE,
    'stdout': subprocess.PIPE,
}


class Sub:
    def __init__(self, cmd, **kwds):
        """
        An iterator yielding ``is_err, line`` pairs from stdout and stderr of
        a process.

        Starts a subprocess, and reads lines from both stdout and stderr,
        yielding a series of ``is_err, line`` pairs, where ``is_err`` is true
        if ``line`` came from stderr.

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
        self.kwds = dict(_SUBPROCESS_KWDS, **kwds)

        self.cmd = cmd
        if self.kwds.get('shell'):
            if not isinstance(cmd, str):
                self.cmd = shlex.join(cmd)
        else:
            if isinstance(cmd, str):
                self.cmd = shlex.split(cmd)

        self.proc = None

    @property
    def returncode(self):
        return self.proc and self.proc.returncode

    stderr_first = True

    def __iter__(self):
        with subprocess.Popen(self.cmd, **self.kwds) as self.proc:
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
                        yield is_err, line.decode('utf-8').rstrip('\n')

                data_received = self.proc.poll() is None or data_received


def call(cmd, out=None, err=None, **kwargs):
    """
    Run a subprocess, read lines from its stdin and stderr, and send them
    to callbacks.

    Returns the shell integer error code from the subprocess, where 0 means
    no error.

    ARGUMENTS
        cmd:
            A list or tuple of strings, or a string, to run in a subprocess.

            If shell=True, Popen expects a string, so if ``cmd`` is a list, it
            is joined using shlex.

            If shell=False, Popen expects a list of strings, so if ``cmd`` is a
            string, it is split using shlex.

        out:
          ``out`` is called for each line from the subprocess's stdout,
          if not None.

        err:
          ``err`` is called for each line from the subprocess's stderr,
          if not None.

        kwargs:
            Keyword arguments passed to subprocess.Popen()
    """
    sub = Sub(cmd, **kwargs)
    for is_err, line in sub:
        if is_err:
            err and err(line)
        else:
            out and out(line)
    return sub.returncode


def run(cmd, **kwargs):
    """
    Starts a subprocess ``p``, reads lines from stdout and stderr into two
    arrays ``out`` and ``err``, then returns a triple:
        ``out, err, p.returncode``

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
    out, err = [], []
    error_code = call(cmd, out.append, err.append, **kwargs)
    return out, err, error_code


def log(cmd, out='  ', err='* ', print=print, **kwargs):
    """
    Runs a command as a  subprocess, reads lines from stdin and stderr, and
    prints them.

    Returns the shell integer error code from the subprocess, where 0 means
    no error.

    ARGUMENTS
        cmd:
            A list or tuple of strings, or a string, to run in a subprocess.

            If shell=True, Popen expects a string, so if ``cmd`` is a list, it
            is joined using shlex.

            If shell=False, Popen expects a list of strings, so if ``cmd`` is a
            string, it is split using shlex.

        out:
            Prefix for each line to stdout

        err:
            Prefix for each line to stderr

        print:
            a function that accepts individual strings

        kwargs:
            Keyword arguments passed to subprocess.Popen()
    """
    return call(
        cmd,
        out=lambda x: print(out + x),
        err=lambda x: print(err + x),
        **kwargs
    )
