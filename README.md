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

`call_in_thread` and its deprecated alias `call_async` currently wait for the
subprocess before returning, despite their names. A separate nonblocking API is
planned. Output ordering between `stdout` and `stderr` is unspecified.

### Nonblocking output stream

`start()` is the opt-in nonblocking API. It starts the process immediately and
yields `(is_stdout, text)` events while it runs. `wait(timeout)` returns `None`
when the timeout expires without terminating the process. Consume the events
before `close()`, which waits for normal completion and reader shutdown.

    stream = sproc.start(CMD)
    for is_stdout, line in stream:
        print('out' if is_stdout else 'err', line, end='')
    returncode = stream.close()

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
