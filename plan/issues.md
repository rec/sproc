# Possible issues

This is an inventory of risks in the current implementation, not a commitment
to change its public API. Items marked **observed** follow directly from the
source or tests; the rest need focused reproduction before a fix is chosen.

## Liveness and concurrency

1. **`call_in_thread()` is synchronous.** **Observed.** It starts reader
   threads inside `with subprocess.Popen(...)`. Leaving that context waits for
   the child process, so the method cannot return until the process exits,
   despite its name and documentation. The existing async test does not measure
   the time at which the method returns.
2. **A blocked callback can stall the child.** If a callback blocks, its reader
   thread stops draining that stream. The child can then block on a full pipe,
   preventing process completion and the caller's return.
3. **Children that inherit output descriptors can prevent completion.** A
   spawned descendant that keeps stdout or stderr open delays EOF, so the
   iterator can wait indefinitely for its two completion sentinels after the
   original child has exited.
4. **There is no timeout or process-group cancellation policy.** A hung child,
   shell, or descendant has no bounded operation. Killing only the direct
   process may leave descendants alive, particularly when `shell=True`.
5. **One `Sub` instance is unsafe to reuse concurrently.** `self.proc` and the
   shared thread list are overwritten by each run. Existing reader threads then
   consult the new process for streams and polling.
6. **The event queue is unbounded.** A process that writes faster than the
   iterator consumes can grow memory without limit.
7. **Chunk mode is not necessarily incremental.** `by_lines=False` calls
   `stream.read()`, which commonly waits for EOF. That contradicts the useful
   expectation that chunks arrive while a long-running process is active.

## Process lifecycle and error handling

1. **`returncode` and `kill()` can access `self.proc` before it exists.**
   **Observed.** The attribute is assigned only after a process starts, but
   both public members read it unconditionally. During execution,
   `Popen.returncode` can also be `None`, although `returncode` is annotated as
   an `int`.
2. **Reader and callback failures are not reported to the caller.** An
   exception in a daemon reader thread, including a decode or callback error,
   can lose output while the caller only receives the process return code.
3. **The EOF sentinel is overloaded.** `None` means a stream ended, while an
   empty read is also treated as completion. That is conventional for pipe EOF,
   but it makes a future binary or nonblocking implementation easy to get
   wrong.
4. **Stream ordering is intentionally nondeterministic but undocumented.** Two
   reader threads race to put events into one queue. Consumers cannot infer the
   original ordering between stdout and stderr.

## Text and binary data

1. **The default path assumes UTF-8.** `Popen` normally produces bytes here,
   then each item is decoded with `utf8`. Output in the locale encoding, a
   tool-specific encoding, or arbitrary binary data raises `UnicodeDecodeError`
   in the reader thread.
2. **Encoding and decoding errors are not part of Sproc's API.** Callers can
   pass Popen's `text`, `encoding`, and `errors` arguments, but their interaction
   with Sproc's manual decode is undocumented and untested.
3. **Line and chunk semantics need a contract.** The library returns trailing
   newlines when present and may return a whole stream in chunk mode. Decide
   whether Sproc is text-only, binary-capable, or exposes separate APIs.

## Public API and documentation

1. **The README's primary iteration example is invalid.** **Observed.**
   `for ok, line in sproc.Sub(CMD) as sp:` is not Python syntax, and `Sub` does
   not implement `__enter__` or `__exit__`.
2. **`Sub` and `ok` obscure their meanings.** `Sub` does not say that it wraps a
   subprocess, while `ok` identifies stdout rather than whether the process or
   line succeeded. A stream enum or `is_stdout` would be clearer.
3. **`call_async` conflicts with `call_in_thread`.** It is documented only by a
   deprecation comment, returns `None`, and currently inherits the blocking
   behavior of `call_in_thread`.
4. **Some documentation is inaccurate or confusing.** `log()` says it reads
   stdin and stderr even though it reads stdout and stderr; the prose also has
   several spelling errors. The behavior, return timing, callback threading,
   and command-normalization rules need explicit documentation.
5. **Popen options are accepted as untyped keyword arguments.** Invalid
   combinations are deferred to process launch, and the supported subset cannot
   be discovered from Sproc's own API.

## Platform compatibility

1. **Command parsing is POSIX-specific.** `shlex.split()` and `shlex.join()`
   implement POSIX shell conventions, not Windows `cmd.exe` or PowerShell
   quoting. Passing a command string, a sequence, and `shell=True` can therefore
   produce materially different commands on Windows.
2. **The tests require Unix tools and messages.** They invoke `ls` and assert
   the English text `No such file or directory`, so they do not run on Windows
   and can fail under a non-English Unix locale.
3. **Shell and process-tree termination vary by platform.** Shell lookup,
   signal delivery, process groups, inherited handles, and whether console
   windows appear differ across Linux, macOS, and Windows. The current direct
   `kill()` API does not state a cross-platform contract.
4. **Text defaults vary by environment.** Locale and Windows code-page defaults
   make the current implicit UTF-8 conversion especially fragile outside the
   tested macOS environment.

## Missing or undecided features

1. A real nonblocking launch API with a documented lifecycle and reliable
   `join()`/return-code semantics.
2. Timeouts, cancellation, and an explicit policy for shell children and
   process trees.
3. Configurable text decoding and a binary-output API, including error policy.
4. A valid context-manager API, if the README's intended `as sp` workflow is
   retained.
5. Deterministic or explicitly best-effort event ordering, plus backpressure or
   bounded buffering.
6. A portable test command built from `sys.executable`, rather than `ls`, with
   tests for slow callbacks, non-UTF-8 output, timeout/cancellation, concurrent
   instances, and Windows command handling.

## Suggested investigation order

1. Specify the synchronous and asynchronous lifecycle contract, then add a
   timing test that proves `call_in_thread()` returns before a sleeping child.
2. Decide the supported text/binary model and add encoding fixtures before
   changing reader behavior.
3. Define cancellation and process-tree behavior per platform, then validate it
   on Linux and Windows as well as macOS.
4. Replace the platform-dependent tests and correct the public examples before
   advertising cross-platform support.
