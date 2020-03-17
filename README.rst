run_subprocess:
--------------------

⛏️subprocesses for subhumanses  ⛏️
=========================================

Run a command in a subprocess, read stdin and stderr, and send their data to
callbacks.

Returns the shell integer error code from the subprocess, where 0 means
no error.

Examples:

.. code-block:: python

   run_subprocess.run('ls')  # Runs the ls command and prints it on the terminal




cmd:
    A list or tuple of strings, or a string.

    If shell=True, Popen expects a string, so if ``cmd`` is a list, it is
    joined with spaces.

    If shell=False, Popen expects a list of strings, so if ``cmd`` is a
    string, it is split using shlex

out:
    ``out`` is called for each line in the subprocess's stdout

err:
    ``err`` is called for each line in the subprocess's stderr

sleep:
    How long to sleep between checking the processes, in seconds

count:
    Maximum number of lines to retrieve at a time from the streams stdout
    and stderr. If count is empty, retrieve lines until the stream blocks.

kwds:
    Keywords that are passed to subprocess.Popen
