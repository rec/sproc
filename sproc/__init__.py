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

import codecs
import functools
import shlex
import subprocess
from collections.abc import Callable, Iterator, Sequence
from queue import Queue
from threading import BoundedSemaphore, Event, Thread
from typing import Any, Literal, Optional, Union, cast

__all__ = (
    'OutputQueueFullError',
    'ProcessStream',
    'Sub',
    'call',
    'call_in_thread',
    'log',
    'run',
    'start',
)

DEFAULTS = {'stderr': subprocess.PIPE, 'stdout': subprocess.PIPE}

Callback = Optional[Callable[..., Any]]
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

    def __init__(self, cmd: Cmd, *, by_lines: bool = True, **kwargs: Any) -> None:
        if 'stdout' in kwargs or 'stderr' in kwargs:
            raise ValueError('Cannot set stdout or stderr')

        self.cmd = cmd
        self.by_lines = by_lines
        self.kwargs = dict(kwargs, **DEFAULTS)
        self.proc: subprocess.Popen[Any] | None = None
        self._reader_error: UnicodeDecodeError | OSError | None = None
        self._threads: list[Thread] = []

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

    @property
    def is_running(self) -> bool:
        """Whether the current subprocess has started and has not exited."""
        return self.proc is not None and self.proc.poll() is None

    @property
    def reader_error(self) -> UnicodeDecodeError | OSError | None:
        """The first decoding or I/O error raised by a stream reader."""
        return self._reader_error

    def __iter__(self) -> Iterator[tuple[bool, str]]:
        """
        Yields a sequence of `ok, line` pairs from `stdout` and `stderr` of
        a subprocess, where `ok` is `True` if `line` came from `stdout`
        and `False` if it came from `stderr`.

        After iteration is done, the `.returncode` property contains
        the error code from the subprocess, an integer where 0 means no error.
        """
        queue: Queue[tuple[bool, str | None]] = Queue()

        with subprocess.Popen(self.cmd, **cast(Any, self.kwargs)) as self.proc:
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
        """Deprecated alias for the currently blocking `call_in_thread()`."""
        return self.call_in_thread(out, err)

    def call_in_thread(self, out: Callback = None, err: Callback = None) -> None:
        """
        Run the subprocess and call function `out` with lines from `stdout`,
        and function `err` with lines from `stderr`.

        Despite its historical name, this method waits for the subprocess before
        returning. A nonblocking replacement will be introduced separately.

        Args:
            out: If not None, `out` is called for each line from the
                subprocess's stdout

            err: If not None, `err` is called for each line from the
                subprocess's stderr,
        """
        with subprocess.Popen(self.cmd, **cast(Any, self.kwargs)) as self.proc:
            callback = self._callback(out, err)
            for ok in False, True:
                self._start_thread(ok, callback)

    def run(self) -> tuple[list[str], list[str], int]:
        """
        Reads lines from `stdout` and `stderr` into two lists `out` and `err`,
        then returns a tuple `(out, err, returncode)`
        """
        out: list[str] = []
        err: list[str] = []

        self.call(out.append, err.append)
        return out, err, self.returncode

    def log(
        self, out: str = '  ', err: str = '! ', print: Callable[..., None] = print
    ) -> int:
        """
        Read lines from `stdout` and `stderr` and prints them with prefixes

        Returns the shell integer error code from the subprocess, where 0 means
        no error.

        Args:
            out: The contents of `out` prepends strings from stdout
            err: The contents of `err` prepends strings from stderr
            print: A function that accepts individual strings
        """
        return self.call(lambda x: print(out + x), lambda x: print(err + x))

    def join(self, timeout: int | None = None) -> None:
        """Join the stream handling threads"""
        for th in self._threads:
            th.join(timeout)

    def kill(self) -> None:
        """Kill the running process, if any"""
        if self.proc:
            self.proc.kill()

    def _start_thread(
        self, ok: bool, callback: Callable[[bool, str | None], None]
    ) -> None:
        def read_stream() -> None:
            proc = self.proc
            assert proc is not None
            try:
                stream = proc.stdout if ok else proc.stderr
                assert stream is not None
                line = '.'
                while line or proc.poll() is None:
                    try:
                        if self.by_lines:
                            line = stream.readline()
                        else:
                            line = stream.read()

                        if line and not isinstance(line, str):
                            line = line.decode('utf8')
                    except (OSError, UnicodeDecodeError) as error:
                        if self._reader_error is None:
                            self._reader_error = error
                        return
                    if line:
                        callback(ok, line)
            finally:
                callback(ok, None)

        th = Thread(target=read_stream, daemon=True)
        th.start()
        self._threads.append(th)

    def _callback(
        self, out: Callable[..., Any] | None, err: Callable[..., Any] | None
    ) -> Callable[[bool, str | None], Any]:
        if out and err:
            return lambda ok, line: line and (out(line) if ok else err(line))
        if out:
            return lambda ok, line: line and ok and out(line)
        if err:
            return lambda ok, line: line and not ok and err(line)
        else:
            return lambda ok, line: None


class OutputQueueFullError(RuntimeError):
    """A bounded ProcessStream queue could not retain all output."""


class ProcessStream:
    """One immediately-started subprocess and its output event stream.

    Iterate once to receive `(is_stdout, text)` or `(is_stdout, bytes)` events.
    `wait()` returns the process return code, or `None` when its timeout expires
    without terminating the process. `close()` waits for the process and its
    reader threads.
    """

    def __init__(
        self,
        cmd: Cmd,
        *,
        by_lines: bool = True,
        chunk_size: int | None = None,
        encoding: str | None = 'utf8',
        errors: str = 'strict',
        max_queue_size: int | None = None,
        overflow: Literal['raise'] | None = None,
        **kwargs: Any,
    ) -> None:
        if any(
            name in kwargs
            for name in ('stderr', 'stdout', 'text', 'universal_newlines')
        ):
            raise ValueError('Cannot set stdout, stderr, text, or universal_newlines')
        if by_lines:
            if chunk_size is not None:
                raise ValueError('chunk_size requires by_lines=False')
        elif chunk_size is None or chunk_size <= 0:
            raise ValueError('chunk mode requires a positive chunk_size')
        if max_queue_size is None:
            if overflow is not None:
                raise ValueError('overflow requires max_queue_size')
        elif max_queue_size <= 0:
            raise ValueError('max_queue_size must be positive')
        elif overflow != 'raise':
            raise ValueError("bounded queues require overflow='raise'")
        if encoding is not None:
            codecs.getincrementaldecoder(encoding)(errors)

        shell = kwargs.get('shell', False)
        if isinstance(cmd, str):
            command: Cmd = cmd if shell else shlex.split(cmd)
        else:
            command = shlex.join(cmd) if shell else cmd

        self._queue: Queue[tuple[bool, str | bytes | None]] = Queue(
            0 if max_queue_size is None else max_queue_size + 2
        )
        self._event_slots = (
            None if max_queue_size is None else BoundedSemaphore(max_queue_size)
        )
        self._queue_full = Event()
        self._by_lines = by_lines
        self._chunk_size = chunk_size
        self._encoding = encoding
        self._errors = errors
        self._reader_error: (
            LookupError | UnicodeDecodeError | OSError | OutputQueueFullError | None
        ) = None
        self._iterated = False
        self._process: subprocess.Popen[Any] = subprocess.Popen(
            command, **cast(Any, dict(kwargs, **DEFAULTS))
        )
        self._threads = [
            Thread(target=self._read_stream, args=(ok,), daemon=True)
            for ok in (False, True)
        ]
        for thread in self._threads:
            thread.start()

    @property
    def is_running(self) -> bool:
        """Whether the subprocess has not exited."""
        return self._process.poll() is None

    @property
    def reader_error(
        self,
    ) -> LookupError | UnicodeDecodeError | OSError | OutputQueueFullError | None:
        """The first reader codec, I/O, or bounded-queue error."""
        return self._reader_error

    @property
    def returncode(self) -> int | None:
        """The subprocess return code, or `None` while it is still running."""
        return self._process.poll()

    def __iter__(self) -> Iterator[tuple[bool, str | bytes]]:
        """Yield output events once, until both output streams close."""
        if self._iterated:
            raise RuntimeError('ProcessStream output can be iterated only once')
        self._iterated = True

        finished = 0
        while finished < 2:
            is_stdout, line = self._queue.get()
            if line is None:
                finished += 1
            else:
                if self._event_slots is not None:
                    self._event_slots.release()
                yield is_stdout, line
        if self._queue_full.is_set():
            assert isinstance(self._reader_error, OutputQueueFullError)
            raise self._reader_error

    def wait(self, timeout: float | None = None) -> int | None:
        """Wait for the subprocess, returning `None` when `timeout` expires."""
        try:
            return self._process.wait(timeout)
        except subprocess.TimeoutExpired:
            return None

    def join(self, timeout: float | None = None) -> bool:
        """Join reader threads and report whether both have stopped."""
        for thread in self._threads:
            thread.join(timeout)
        return all(not thread.is_alive() for thread in self._threads)

    def close(self) -> int:
        """Wait for normal completion, join readers, and close output streams."""
        returncode = self.wait()
        assert returncode is not None
        self.join()
        for stream in self._process.stdout, self._process.stderr:
            if stream is not None:
                stream.close()
        return returncode

    def terminate(self) -> None:
        """Terminate the direct process without affecting descendants."""
        if self._process.poll() is None:
            try:
                self._process.terminate()
            except ProcessLookupError:
                pass

    def kill(self) -> None:
        """Kill the direct process without affecting descendants."""
        if self._process.poll() is None:
            try:
                self._process.kill()
            except ProcessLookupError:
                pass

    def _read_stream(self, is_stdout: bool) -> None:
        stream = self._process.stdout if is_stdout else self._process.stderr
        assert stream is not None
        decoder = None
        if self._encoding is not None:
            decoder = codecs.getincrementaldecoder(self._encoding)(self._errors)
        try:
            while True:
                try:
                    if self._by_lines:
                        line = stream.readline()
                    else:
                        assert self._chunk_size is not None
                        line = getattr(stream, 'read1', stream.read)(self._chunk_size)
                    if not line:
                        if decoder is not None and (
                            text := decoder.decode(b'', final=True)
                        ):
                            self._put_event(is_stdout, text)
                        return
                    if decoder is not None:
                        line = decoder.decode(line)
                except (LookupError, OSError, UnicodeDecodeError) as error:
                    if self._reader_error is None:
                        self._reader_error = error
                    return
                if line:
                    self._put_event(is_stdout, line)
        finally:
            self._queue.put((is_stdout, None))

    def _put_event(self, is_stdout: bool, line: str | bytes) -> None:
        if self._queue_full.is_set():
            return
        if self._event_slots is None or self._event_slots.acquire(blocking=False):
            self._queue.put((is_stdout, line))
        else:
            self._reader_error = OutputQueueFullError(
                'ProcessStream output queue is full'
            )
            self._queue_full.set()


def call(cmd: Cmd, out: Callback = None, err: Callback = None, **kwargs: Any) -> int:
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


def start(
    cmd: Cmd,
    *,
    by_lines: bool = True,
    chunk_size: int | None = None,
    encoding: str | None = 'utf8',
    errors: str = 'strict',
    max_queue_size: int | None = None,
    overflow: Literal['raise'] | None = None,
    **kwargs: Any,
) -> ProcessStream:
    """Start a subprocess immediately and return its output event stream."""
    return ProcessStream(
        cmd,
        by_lines=by_lines,
        chunk_size=chunk_size,
        encoding=encoding,
        errors=errors,
        max_queue_size=max_queue_size,
        overflow=overflow,
        **kwargs,
    )


def call_in_thread(
    cmd: Cmd, out: Callback = None, err: Callback = None, **kwargs: Any
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
def run(cmd: Cmd, **kwargs: Any) -> tuple[list[str], list[str], int]:
    return Sub(cmd, **kwargs).run()


def log(
    cmd: Cmd,
    out: str = '  ',
    err: str = '! ',
    print: Callable[..., None] = print,
    **kwargs: Any,
) -> int:
    """
    Args:
        cmd:  The command to run in a subprocess
        out: The contents of `out` prepends strings from stdout
        err: The contents of `err` prepends strings from stderr
        print: A function that accepts individual strings
    """
    return Sub(cmd, **kwargs).log(out, err, print)
