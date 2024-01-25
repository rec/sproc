"""
# ⛏️sproc: subprocesseses for subhumanses  ⛏

Run a command in a subprocess and yield lines of text from `stdout` and
`stderr` independently.

Useful for handling long-running proceesses that write to both `stdout` and
`stderr`.

### Simple Example

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

import functools
import shlex
import subprocess
import typing as t
from queue import Queue
from threading import Thread
from typing import Callable, List, Mapping, Optional, Sequence, Union

__all__ = 'Sub', 'call', 'call_in_thread', 'run', 'log'

DEFAULTS = {'stderr': subprocess.PIPE, 'stdout': subprocess.PIPE}

Callback = Optional[t.Callable[..., t.Any]]
Cmd = Union[str, Sequence[str]]


class Sub:
    """
    Sub is a class to Iterate over lines or chunks of text from a subprocess.

    If `by_lines` is true, use readline() to get each new item;
    if false, use read1().

    Args:
      cmd:  The command to run in a subprocess

      by_lines:  If `by_lines` is true, `Sub` uses readline() to get each new
          item;  otherwise, it uses read1() to get each chunk as it comes.

      kwargs: The arguments to subprocess.Popen.

          If `kwargs['shell']` is true, `Popen` expects a string,
          and so if `cmd` is not a string, it is joined using `shlex`.

          If `kwargs['shell']` is false, `Popen` expects a list of strings,
          and so if `cmd` is a string, it is split using `shlex`.
    """

    @functools.wraps(subprocess.Popen)
    def __init__(self, cmd: Cmd, *, by_lines: bool = True, **kwargs: t.Any) -> None:
        if 'stdout' in kwargs or 'stderr' in kwargs:
            raise ValueError('Cannot set stdout or stderr')

        self.cmd = cmd
        self.by_lines = by_lines
        self.kwargs = dict(kwargs, **DEFAULTS)
        self._threads: List[Thread] = []

        shell = kwargs.get('shell', False)
        if isinstance(cmd, str):
            if not shell:
                self.cmd = shlex.split(cmd)
        else:
            if shell:
                self.cmd = shlex.join(cmd)

    @property
    def returncode(self) -> int:
        return self.proc.returncode if self.proc else 0

    def __iter__(self) -> t.Iterator[t.Tuple[bool, str]]:
        """
        Yields a sequence of `ok, line` pairs from `stdout` and `stderr` of
        a subprocess, where `ok` is `True` if `line` came from `stdout`
        and `False` if it came from `stderr`.

        After iteration is done, the `.returncode` property contains
        the error code from the subprocess, an integer where 0 means no error.
        """
        queue: Queue[t.Tuple[bool, t.Optional[str]]] = Queue()

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

    def call(self, out: Callback = None, err: Callback = None) -> int:
        """
        Run the subprocess, and call function `out` with lines from
        `stdout` and function `err` with lines from `stderr`.

        Blocks until the subprocess is complete: the callbacks to `out` and
        'err` are on the current thread.

        Args:
            out: if not None, `out` is called for each line from the
                subprocess's stdout

            err: if not None, `err` is called for each line from the
                subprocess's stderr,
        """
        callback = self._callback(out, err)
        for ok, line in self:
            callback(ok, line)

        return self.returncode

    def call_async(self, out: Callback = None, err: Callback = None) -> None:
        # DEPRECATED: now called "call_in_thread"
        return self.call_in_thread(out, err)

    def call_in_thread(self, out: Callback = None, err: Callback = None) -> None:
        """
        Run the subprocess, and asynchronously call function `out` with lines
        from `stdout`, and function `err` with lines from `stderr`.

        Does not block - immediately returns.

        Args:
            out: If not None, `out` is called for each line from the
                subprocess's stdout

            err: If not None, `err` is called for each line from the
                subprocess's stderr,
        """
        with subprocess.Popen(self.cmd, **self.kwargs) as self.proc:
            callback = self._callback(out, err)
            for ok in False, True:
                self._start_thread(ok, callback)

    def run(self) -> t.Tuple[t.List[str], t.List[str], int]:
        """
        Reads lines from `stdout` and `stderr` into two lists `out` and `err`,
        then returns a tuple `(out, err, returncode)`
        """
        out: t.List[str] = []
        err: t.List[str] = []

        self.call(out.append, err.append)
        return out, err, self.returncode

    def log(
        self, out: str = '  ', err: str = '! ', print: t.Callable[..., None] = print
    ) -> int:
        """
        Read lines from `stdin` and `stderr` and prints them with prefixes

        Returns the shell integer error code from the subprocess, where 0 means
        no error.

        Args:
            out: The contents of `out` prepends strings from stdout
            err: The contents of `err` prepends strings from stderr
            print: A function that accepts individual strings
        """
        return self.call(lambda x: print(out + x), lambda x: print(err + x))

    def join(self, timeout: Optional[int] = None) -> None:
        """Join the stream handling threads"""
        for t in self._threads:
            t.join(timeout)

    def kill(self) -> None:
        """Kill the running process, if any"""
        if self.proc:
            self.proc.kill()

    def _start_thread(
        self, ok: bool, callback: t.Callable[[bool, t.Optional[str]], None]
    ) -> None:
        def read_stream() -> None:
            try:
                stream = self.proc.stdout if ok else self.proc.stderr
                assert stream is not None
                line = '.'
                while line or self.proc.poll() is None:
                    if self.by_lines:
                        line = stream.readline()
                    else:
                        line = stream.read()

                    if line:
                        if not isinstance(line, str):
                            line = line.decode('utf8')
                        callback(ok, line)
            finally:
                callback(ok, None)

        th = Thread(target=read_stream, daemon=True)
        th.start()
        self._threads.append(th)

    def _callback(
        self,
        out: t.Optional[t.Callable[..., t.Any]],
        err: t.Optional[t.Callable[..., t.Any]],
    ) -> t.Callable[[bool, t.Optional[str]], t.Any]:
        if out and err:
            return lambda ok, line: line and (out(line) if ok else err(line))
        if out:
            return lambda ok, line: line and ok and out(line)
        if err:
            return lambda ok, line: line and not ok and err(line)
        else:
            return lambda ok, line: None


def call(cmd: Cmd, out: Callback = None, err: Callback = None, **kwargs: t.Any) -> int:
    """
    Args:
      cmd:  The command to run in a subprocess

      out: if not None, `out` is called for each line from the
          subprocess's stdout

      err: if not None, `err` is called for each line from the
          subprocess's stderr,

      kwargs: The arguments to subprocess.Popen.
    """
    return Sub(cmd, **kwargs).call(out, err)


def call_in_thread(
    cmd: Cmd, out: Callback = None, err: Callback = None, **kwargs: t.Any
) -> None:
    """
    Args:
      cmd:  The command to run in a subprocess

      out: if not None, `out` is called for each line from the
          subprocess's stdout

      err: if not None, `err` is called for each line from the
          subprocess's stderr,

      kwargs: The arguments to subprocess.Popen.
    """
    return Sub(cmd, **kwargs).call_in_thread(out, err)


call_async = call_in_thread


@functools.wraps(Sub.__init__)
def run(cmd: Cmd, **kwargs: t.Any) -> t.Tuple[t.List[str], t.List[str], int]:
    return Sub(cmd, **kwargs).run()


def log(
    cmd: Cmd,
    out: str = '  ',
    err: str = '! ',
    print: t.Callable[..., None] = print,
    **kwargs: t.Any,
) -> int:
    """
    Args:
        cmd:  The command to run in a subprocess
        out: The contents of `out` prepends strings from stdout
        err: The contents of `err` prepends strings from stderr
        print: A function that accepts individual strings
    """
    return Sub(cmd, **kwargs).log(out, err, print)
