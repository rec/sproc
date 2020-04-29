##################################################
⛏️sproc: subprocesseses for subhumanses  ⛏
##################################################

Run a command in a subprocess and yield lines of text from stdout and stderr

*********
EXAMPLES
*********

.. code-block:: python

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

***
API
***

Methods on ``class sproc.Sub:``
===============================

``Sub.__init__(self, cmd, **kwds)``
-----------------------------------

    Iterate over lines of text from a subprocess.

    If ``kwargs['shell']`` is true, ``Popen`` expects a string,
    and so if ``cmd`` is not a string, it is joined using ``shlex``.

    If ``kwargs['shell']`` is false, ``Popen`` expects a list of strings,
    and so if ``cmd`` is a string, it is split using ``shlex``.

    ARGUMENTS
      cmd:
        The command to run in a subprocess: a string or a list or tuple of strings

      kwargs:
        Keyword arguments passed to subprocess.Popen()

``Sub.__iter__(self)``
----------------------

            Yields a sequence of ``ok, line`` pairs from ``stdout`` and ``stderr`` of
            a subprocess, where ``ok`` is ``True`` if ``line`` came from ``stdout``
            and ``False`` if it came from ``stderr``.

            After iteration is done, the ``.returncode`` property contains
            the error code from the subprocess, an integer where 0 means no error.
        

``Sub.call(self, out=None, err=None)``
--------------------------------------

    Run the subprocess, and call function ``out`` with lines from
    ``stdout`` and function ``err`` with lines from ``stderr``.

    Blocks until the subprocess is complete: the callbacks to ``out`` and
    'err`` are on the current thread.

    ARGUMENTS
      out:
        if not None, ``out`` is called for each line from the subprocess's stdout

      err:
        if not None, ``err`` is called for each line from the subprocess's stderr,

``Sub.call_async(self, out=None, err=None)``
--------------------------------------------

    Run the subprocess, and asynchronously call function ``out`` with lines
    from ``stdout``, and function ``err`` with lines from ``stderr``.

    Does not block - immediately returns.

    ARGUMENTS
      out:
        if not None, ``out`` is called for each line from the subprocess's stdout

      err:
        if not None, ``err`` is called for each line from the subprocess's stderr,

``Sub.run(self)``
-----------------

    Reads lines from ``stdout`` and ``stderr`` into two lists ``out`` and ``err``,
    then returns a tuple ``(out, err, returncode)``

``Sub.log(self, out='  ', err='! ', print=<built-in function print>)``
----------------------------------------------------------------------

    Read lines from ``stdin`` and ``stderr`` and prints them with prefixes

    Returns the shell integer error code from the subprocess, where 0 means
    no error.

    ARGUMENTS
      out:
        Prefix for printing lines from stdout

      err:
        Prefix for printing lines from stderr


Functions
=========

``sproc.call(cmd, out=None, err=None, **kwds)``
-----------------------------------------------

    Run the subprocess, and call function ``out`` with lines from
    ``stdout`` and function ``err`` with lines from ``stderr``.

    Blocks until the subprocess is complete: the callbacks to ``out`` and
    'err`` are on the current thread.

    ARGUMENTS
      cmd:
        The command to run in a subprocess: a string or a list or tuple of strings

      out:
        if not None, ``out`` is called for each line from the subprocess's stdout

      err:
        if not None, ``err`` is called for each line from the subprocess's stderr,

      kwargs:
        Keyword arguments passed to subprocess.Popen()


``sproc.call_async(cmd, out=None, err=None, **kwds)``
-----------------------------------------------------

    Run the subprocess, and asynchronously call function ``out`` with lines
    from ``stdout``, and function ``err`` with lines from ``stderr``.

    Does not block - immediately returns.

    ARGUMENTS
      cmd:
        The command to run in a subprocess: a string or a list or tuple of strings

      out:
        if not None, ``out`` is called for each line from the subprocess's stdout

      err:
        if not None, ``err`` is called for each line from the subprocess's stderr,

      kwargs:
        Keyword arguments passed to subprocess.Popen()


``sproc.run(cmd, **kwds)``
--------------------------

    Reads lines from ``stdout`` and ``stderr`` into two lists ``out`` and ``err``,
    then returns a tuple ``(out, err, returncode)``

    ARGUMENTS
      cmd:
        The command to run in a subprocess: a string or a list or tuple of strings

      kwargs:
        Keyword arguments passed to subprocess.Popen()


``sproc.log(cmd, out='  ', err='! ', print=<built-in function print>, **kwds)``
-------------------------------------------------------------------------------

    Read lines from ``stdin`` and ``stderr`` and prints them with prefixes

    Returns the shell integer error code from the subprocess, where 0 means
    no error.

    ARGUMENTS
      cmd:
        The command to run in a subprocess: a string or a list or tuple of strings

      out:
        Prefix for printing lines from stdout

      err:
        Prefix for printing lines from stderr

      kwargs:
        Keyword arguments passed to subprocess.Popen()