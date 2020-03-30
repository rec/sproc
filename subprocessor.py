import itertools
import shlex
import subprocess
import time

__version__ = '0.9.0'

_SUBPROCESS_KWDS = {
    'shell': False,
    'stderr': subprocess.PIPE,
    'stdout': subprocess.PIPE,
}


class Call:
    def __init__(self, cmd, sleep=0, count=None, **kwds):
        """
        Run a command in a subprocess, and yield is_error, line pairs.

        cmd:
            A list or tuple of strings, or a string, to run in a subprocess.

            If shell=True, Popen expects a string, so if ``cmd`` is a list, it
            is joined using shlex.

            If shell=False, Popen expects a list of strings, so if ``cmd`` is a
            string, it is split using shlex

        sleep:
            How long to sleep between checking the processes, in seconds

        count:
            Maximum number of lines to retrieve at a time from the streams
            stdout and stderr. If count is empty, retrieve lines until the
            stream blocks.

        kwds:
            Keywords that are passed to subprocess.Popen
        """
        self.kwds = dict(_SUBPROCESS_KWDS, **kwds)
        if self.kwds.get('shell'):
            if isinstance(cmd, str):
                self.cmd = cmd
            else:
                self.cmd = shlex.join(cmd)
        elif isinstance(cmd, str):
            self.cmd = shlex.split(cmd)
        else:
            self.cmd = cmd
        self.sleep = sleep
        self.counter = range(count) if count else itertools.count()
        self.returncode = None

    def __iter__(self):
        """Yield a series of ``error, line`` pairs from the subprocess cmd"""

        with subprocess.Popen(self.cmd, **self.kwds) as p:
            while True:
                got_data = False
                for is_error in True, False:
                    stream = (p.stdout, p.stderr)[is_error]
                    for i in self.counter:
                        line = stream.readline()
                        if not line:
                            break
                        got_data = True
                        yield is_error, line.decode('utf-8').rstrip('\n')

                if not (p.poll() is None or got_data):
                    self.returncode = p.returncode
                    break

                if self.sleep:
                    time.sleep(self.sleep)

    def communicate(self, out=print, err=None):
        """
        Run the subprocess, read lines from stdin and stderr, and send them to
        callbacks.

        Returns the shell integer error code from the subprocess, where 0 means
        no error.

        out:
            ``out`` is called for each line in the subprocess's stdout

        err:
            ``err`` is called for each line in the subprocess's stderr
        """
        for is_error, line in self:
            (err if err and is_error else out)(line)

        return self.returncode
