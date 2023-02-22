# ⛏ `sproc`: Subprocesseses for subhumanses ⛏

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


### [API Documentation](https://rec.github.io/sproc#sproc--api-documentation)
