import functools
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
        The callback for stdout from the subprocess

    err:
        The callback for stderr from the subprocess

    sleep:
        How long to sleep between checking the process

    count:
        Maximum number lines to retrieve at a time, from stdout or stderr

    kwds:
        Keywords that are passed to subprocess.Popen
    """
    err = err or out
    kwds = dict(_SUBPROCESS_KWDS, **kwds)

    if kwds.get('shell'):
        if not isinstance(cmd, str):
            cmd = ' '.join(cmd)

    elif isinstance(cmd, str):
        cmd = shlex.split(cmd)

    with subprocess.Popen(cmd, **kwds) as p:
        read = functools.partial(read_lines, count=count)

        while read(p.stdout, out) or read(p.stderr, err) or p.poll() is None:
            if sleep:
                time.sleep(sleep)

    return p.returncode


def run_to_list(cmd, **kwds):
    """
    Redirect the stdout of a subprocess to a list, and return that list.

    If the parameter `err` is not set, then error messages will also be
    added to the list.

    """
    out = []
    return run(cmd, out=out.append, **kwds), out


def read_lines(stream, callback, count=None):
    """
    Reads lines of text from a stream and sends them to a callback, until the
    stream blocks.

    Returns the number of lines read.

    If `count` is not None, at most `count` lines are read.

    """
    for i in itertools.count() if count is None else range(count):
        line = stream.readline()
        if line:
            callback(line.decode('utf-8').rstrip('\n'))
        else:
            return i

    return i + 1
