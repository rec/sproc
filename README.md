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


### [API Documentation](https://rec.github.io/sproc#sproc--api-documentation)
