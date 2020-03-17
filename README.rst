subprocessor:
--------------------

⛏️subprocesses for subhumanses  ⛏️
=========================================

Run a command in a subprocess and yield lines from stdout and stderr

Examples:

.. code-block:: python

   from subprocessor import Call

   for is_error, line in Call('ls foo bar NO_EXIST'):
       print(is_error, line)



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
