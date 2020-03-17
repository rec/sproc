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


def run(cmd, out=print, err=None, sleep=0, count=None, **kwds):
    """
    Run a subprocess, read its stdin and stderr, and send them to error and
    output callbacks.

    Returns the integer error code that the subprocess returned.

    cmd:
        A list or tuple of strings, or a string that is split using shlex

    out:
        `out` is called for each line in the subprocess's stdout

    err:
        `err` is called for each line in the subprocess's stderr

    sleep:
        How long to sleep between checking the processes, in seconds

    count:
        Maximum number of lines to retrieve at a time from the streams stdout
        and stderr. If count is empty, retrieve lines until the stream blocks.

    kwds:
        Keywords that are passed to subprocess.Popen
    """
    err = err or out
    kwds = dict(_SUBPROCESS_KWDS, **kwds)

    def read(stream, callback):
        for i in range(count) if count else itertools.count():
            line = stream.readline()
            if not line:
                return i
            callback(line.decode('utf-8').rstrip('\n'))
        return i + 1

    if kwds.get('shell'):
        if not isinstance(cmd, str):
            cmd = ' '.join(cmd)

    elif isinstance(cmd, str):
        cmd = shlex.split(cmd)

    with subprocess.Popen(cmd, **kwds) as p:
        while read(p.stdout, out) or read(p.stderr, err) or p.poll() is None:
            if sleep:
                time.sleep(sleep)

    return p.returncode
