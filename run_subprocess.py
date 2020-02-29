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


def run(cmd, out=print, err=None, sleep=0, count=0, **kwds):
    """Run a subprocess with separate error and output callbacks"""
    err = err or out

    kwds = dict(_SUBPROCESS_KWDS, **kwds)
    if kwds.get('shell'):
        if not isinstance(cmd, str):
            cmd = ' '.join(cmd)
    elif isinstance(cmd, str):
        cmd = shlex.split(cmd)

    with subprocess.Popen(cmd, **kwds) as p:

        def read(fp, callback):
            for i in range(count) if count else itertools.count():
                line = fp.readline()
                if not line:
                    return i
                callback(line.decode('utf-8').rstrip('\n'))

        while read(p.stdout, out) or read(p.stderr, err) or p.poll() is None:
            if sleep:
                time.sleep(sleep)

    return p.returncode


def run_list(cmd, **kwds):
    out = []
    return run(cmd, out=out.append, **kwds), out
