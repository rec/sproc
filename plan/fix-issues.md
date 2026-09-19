# Compatibility-first issue remediation

Sproc has unknown downstream users, so correctness improvements must not silently
change process launch, output, callback, timing, or error behavior. This plan
uses additive APIs and regression fixtures first. No existing public name should
be removed or given new default behavior in a 2.x release.

## Compatibility contract

Until a documented major release, preserve all of the following:

- `Sub`, `call`, `call_in_thread`, `call_async`, `run`, and `log` remain
  importable with their current arguments.
- String commands retain their current `shlex` normalization; sequence commands
  retain their current handling; `shell=True` remains caller-controlled.
- A callback still receives one positional text value. Iteration still yields
  `(ok, text)`, where `ok=True` means stdout and `ok=False` means stderr.
- `run()` still returns `(stdout_lines, stderr_lines, returncode)`, and `log()`
  retains its prefixes and return value.
- The current default text behavior remains UTF-8 with strict decoding. A new
  encoding policy must be opt-in until a major release.
- Existing output remains unbounded and best-effort ordered. Do not add a
  default queue limit, drop policy, timeout, process-tree kill, or exception
  propagation to an old entry point.

Document every behavior preserved intentionally, including behavior that will
eventually be deprecated. A behavior change requires a release note, a focused
regression test, and an explicit versioning decision.

## Phase 0: establish the compatibility baseline

Before changing implementation behavior, expand the test suite around the
currently supported surface.

1. Replace shell-dependent test commands with child Python scripts launched via
   `sys.executable`. The scripts should write distinct stdout and stderr data,
   exit with selected return codes, and support sleeps and binary writes.
2. Add tests that lock down the current behavior of every public helper:
   command-string splitting, sequence commands, `shell=True`, output callbacks,
   iteration, `run()`, `log()`, `call_async`, and `join()`.
3. Write explicit compatibility tests for output values, trailing newlines,
   callback argument count, stdout/stderr separation, and return codes. Do not
   assert relative ordering between streams unless an ordering contract is
   adopted.
4. Run this suite on supported Python versions and at least Linux, macOS, and
   Windows. Use a UTF-8 locale and a non-UTF-8 or invalid-byte fixture where the
   platform can produce one.
5. Add a documented support matrix: Python versions, operating systems, shells,
   and whether byte output is supported.

The compatibility suite becomes the release gate for every following phase.

## Phase 1: safe fixes and accurate documentation

These changes should not alter a completed process's output or return value.

1. Correct the README and generated API documentation. Replace the invalid
   `for ... as sp` example with a valid iteration example, correct the `log()`
   stdout wording, and explain that cross-stream ordering is unspecified.
2. Document `call_in_thread()` and `call_async()` as currently blocking while a
   replacement is introduced. Do not claim that either is nonblocking before a
   timing test proves it.
3. Initialize internal process state defensively and document the supported
   lifecycle. Do not change the public meaning or type of `returncode` in this
   phase: add a separate opt-in state query if callers need to distinguish
   not-started, running, and finished states.
4. Catch reader-thread failures internally, retain the first failure for
   inspection, and make it observable through a new API. Existing methods must
   continue returning their current values unless the caller opts into the new
   error-reporting behavior.
5. State that a `Sub` instance supports one active invocation only. Do not make
   concurrent reuse appear supported until it has a deliberate lifecycle model.

Release this as a patch or minor version only if the compatibility suite is
unchanged. Documentation and new inspection-only APIs are additive.

## Phase 2: add a real asynchronous API

Do not repair `call_in_thread()` by changing its return timing in place. A
caller may depend on its current accidental blocking behavior.

1. Design a new, clearly named opt-in entry point, such as `start()` or
   `ProcessStream`, that launches immediately and owns exactly one `Popen`
   instance, its reader threads, completion state, and reader failures.
2. Give the new handle explicit operations: iterate or receive events, wait,
   join readers, inspect return code, terminate the direct process, and close.
   Specify which operations are safe before launch completion and after exit.
3. Use local per-invocation state rather than `Sub.proc` and `Sub._threads`, so
   concurrent handles cannot overwrite each other.
4. Add timing tests using a sleeping child: construction returns promptly,
   callbacks occur while the child runs, wait blocks until completion, and
   return code becomes available only after completion.
5. Test callback failure behavior. The new API should expose failures from
   reader or callback execution in a documented way without leaving waiters
   blocked.

Keep `call_in_thread()` and `call_async()` as compatibility wrappers. They may
delegate internally only if their old blocking timing and callback behavior are
preserved exactly. Deprecate them only after at least one documented minor
release with the replacement available; alter their behavior only in a major
release.

## Phase 3: make liveness controls opt-in

The new asynchronous handle may offer controls that old APIs deliberately do
not adopt by default.

1. Add optional timeout support to wait or collection operations. Define the
   timeout result without implicitly killing the child.
2. Add direct-process terminate and kill operations with documented idempotence
   and post-exit behavior. Do not claim that they kill descendants.
3. Consider process-tree control only as an explicitly selected policy. On
   POSIX that may require a new process group; on Windows it requires a tested
   platform-specific approach. Never silently change the old process-group
   behavior.
4. Offer a bounded queue only with an explicit size and overflow policy. Test
   block, fail, and drop policies separately. Retain the old unbounded queue for
   legacy helpers.
5. Reproduce inherited-descriptor hangs with a controlled child/grandchild
   fixture. Document the supported mitigation rather than guessing at a global
   fix.

## Phase 4: add explicit text and binary modes

Do not change the default UTF-8 behavior. Instead add a separate, documented
configuration path on the new API.

1. Define `encoding` and `errors` behavior for text mode, including whether
   they are passed to `Popen` or used by Sproc's reader. Test valid UTF-8,
   non-UTF-8, invalid bytes, and callback values.
2. Add an opt-in binary mode whose callbacks and events receive `bytes`. Do not
   mix `str` and `bytes` in one stream.
3. Define chunk mode precisely. If incremental chunks are promised, implement a
   bounded read size and test delivery before EOF. Preserve legacy
   `by_lines=False` behavior under the old APIs.
4. Publish migration examples for callers that need locale decoding, replacement
   decoding, or raw bytes.

## Phase 5: platform support and command semantics

1. Test every public helper on Linux, macOS, and Windows using only Python child
   commands. Remove assertions about shell error wording and Unix command names.
2. Document the distinction between a string command, a sequence command, and
   `shell=True`. Do not promise that POSIX `shlex` quoting describes Windows
   `cmd.exe` or PowerShell.
3. On Windows, test quoting, paths containing spaces, console-window behavior,
   handle inheritance, direct termination, and shell children. On POSIX, test
   signals, process groups, and descriptor inheritance.
4. Keep the existing command normalization for legacy APIs. If platform-native
   command construction is needed, provide a new explicit API rather than
   changing legacy string parsing.

## Phase 6: naming, deprecation, and major-release decisions

1. Improve documentation before renaming public symbols. Explain `ok` as
   "is stdout" everywhere it appears.
2. Add clearer names only as aliases or new APIs, for example an event type with
   `is_stdout`. Keep `Sub` and the boolean tuple indefinitely through the 2.x
   line.
3. Publish a deprecation schedule with the replacement, earliest removal
   version, migration examples, and release-note callouts. Do not emit a warning
   merely for normal use until users have had at least one minor release to
   adopt the replacement.
4. Reserve semantic changes to `call_in_thread()`, `call_async()`,
   `returncode`, default decoding, chunk delivery, cancellation, and queue
   bounds for a major release. Each requires a migration guide and compatibility
   test comparison.

## Release gates

For each phase:

1. Run unit, static, formatting, and packaging checks.
2. Run the compatibility suite on the supported OS and Python matrix.
3. Add a regression test for every fixed issue before changing code.
4. Review whether a change alters timing, output, exceptions, resource use, or
   process ownership for an existing entry point. If it does, defer it to a new
   opt-in API or a major release.
5. Include exact compatibility guarantees and known limitations in the release
   notes.

The work should stop after any phase whose compatibility evidence is incomplete;
it is safer to document a limitation than to change behavior for unknown users.
