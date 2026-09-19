# ⛏️sproc: subprocesseses for subhumanses  ⛏

Run a command in a subprocess and yield lines of text from `stdout` and
`stderr` independently.

Useful for handling long-running processes that write to both `stdout` and
`stderr`.

### Simple Example

    import sproc

    CMD = 'my-unix-command "My Cool File.txt" No-file.txt'

    sp = sproc.Sub(CMD)
    for is_stdout, line in sp:
        if is_stdout:
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

### Lifecycle and current limitations

One `Sub` instance supports one active invocation. `is_running` reports whether
that invocation is still active, and `reader_error` exposes the first reader
I/O or UTF-8 decoding error. Existing callbacks and return values are unchanged;
callback exceptions retain their existing thread behavior.

`call_in_thread` and its compatibility alias `call_async` currently wait for
the subprocess before returning, despite their names. Output ordering between
`stdout` and `stderr` is unspecified.

### Nonblocking output stream

`start()` is the preferred nonblocking API. It starts the process immediately
and yields tuple-compatible `OutputEvent` values while it runs. `is_stdout`
identifies stdout rather than success, and `text` is the output value.
`wait(timeout)` returns `None` when the timeout expires without terminating the
process. Consume the events before `close()`, which waits for normal completion
and reader shutdown.

    stream = sproc.start(CMD)
    for event in stream:
        print('out' if event.is_stdout else 'err', event.text, end='')
    returncode = stream.close()

The events remain unpackable for callers that prefer `is_stdout, text = event`.

### Compatibility timeline

`call_in_thread()` and `call_async()` remain supported compatibility APIs with
no planned removal version. This release emits no warning for either. A future
minor release may add a migration warning after users have had time to adopt
`ProcessStream`.

### Command semantics

For compatibility, a string command with `shell=False` uses POSIX `shlex`
splitting, including on Windows. A sequence command with `shell=False` is
passed directly to `Popen`. With `shell=True`, a string is passed to the
platform shell unchanged; callers must use the quoting rules of that shell.
Sequence commands with `shell=True` retain their legacy POSIX `shlex` joining.

Use sequence commands when portability matters. Sproc does not promise that a
POSIX-quoted string works in `cmd.exe` or PowerShell.

### Liveness controls

`ProcessStream.wait(timeout)` returns `None` when the timeout expires and does
not terminate the process. `terminate()` and `kill()` are idempotent operations
on the direct child only; they never claim to stop shell children or other
descendants.

For a bounded output queue, pass both a size and `overflow='raise'`. Sproc
continues draining the child after the limit so that the child can finish, then
iteration raises `OutputQueueFullError` after yielding the output that fit.

    stream = sproc.start(CMD, max_queue_size=100, overflow='raise')

A child that gives stdout or stderr to a long-lived descendant can delay stream
EOF after the direct child exits. Keep descendant output separate, for example
by redirecting it to `subprocess.DEVNULL`; Sproc does not guess which process
tree to terminate.

### Text, binary, and chunked output

`ProcessStream` decodes UTF-8 strictly by default. Set `encoding` and `errors`
to choose a text codec and decoding policy. Set `encoding=None` for binary
events: one stream yields either `str` values or `bytes` values, never both.

    text = sproc.start(CMD, encoding='latin-1')
    binary = sproc.start(CMD, encoding=None)

Line mode is the default. For incremental output chunks, set `by_lines=False`
and provide a positive `chunk_size`; each chunk has at most that many bytes
before text decoding. The old helpers retain their EOF-sized chunk behavior.

    chunks = sproc.start(CMD, by_lines=False, chunk_size=4096)


### [API Documentation](https://rec.github.io/sproc#sproc--api-documentation)
