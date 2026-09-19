import shlex
import sys
import unittest

import sproc

EXIT_CODE = 7
STDOUT = ['out-one\n', 'out-two\n', 'café\n']
STDERR = ['err-one\n', 'err-two\n']
CHILD = f"""\
import sys

sys.stdout.write({STDOUT[0]!r})
sys.stdout.write({STDOUT[1]!r})
sys.stdout.write({STDOUT[2]!r})
sys.stdout.flush()
sys.stderr.write({STDERR[0]!r})
sys.stderr.write({STDERR[1]!r})
sys.stderr.flush()
raise SystemExit({EXIT_CODE})
"""
INVALID_UTF8_CHILD = """\
import sys

sys.stdout.buffer.write(b'\\xff\\n')
sys.stdout.buffer.flush()
"""
ASYNC_CHILD = 'pass'
RUNNING_CHILD = """\
import sys
import time

sys.stdout.write('ready\\n')
sys.stdout.flush()
time.sleep(1)
"""
OUTPUT_CHILD = """\
import sys

for line in range(3):
    print(line, flush=True)
"""
LATIN_1_CHILD = """\
import sys

sys.stdout.buffer.write(b'caf\\xe9\\n')
sys.stdout.buffer.flush()
"""
CHUNK_CHILD = """\
import sys
import time

sys.stdout.buffer.write(b'abcdef')
sys.stdout.buffer.flush()
time.sleep(1)
"""
INHERITING_CHILD = """\
import subprocess
import sys

subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(0.5)'])
"""


def command(script: str, *, shell: bool) -> str | list[str]:
    parts = [sys.executable, '-c', script]
    if shell:
        return shlex.join(parts)
    return parts


def string_command(script: str) -> str:
    return shlex.join([sys.executable, '-c', script])


class SprocTest(unittest.TestCase):
    def assert_output(self, out: list[str], err: list[str]) -> None:
        self.assertEqual(out, STDOUT)
        self.assertEqual(err, STDERR)

    def test_iteration_separates_streams(self) -> None:
        for shell in False, True:
            with self.subTest(shell=shell):
                events = list(sproc.Sub(command(CHILD, shell=shell), shell=shell))
                out = [line for ok, line in events if ok]
                err = [line for ok, line in events if not ok]

                self.assert_output(out, err)

    def test_string_and_sequence_commands(self) -> None:
        for value in string_command(CHILD), command(CHILD, shell=False):
            with self.subTest(command_type=type(value)):
                out, err, returncode = sproc.run(value)

                self.assert_output(out, err)
                self.assertEqual(returncode, EXIT_CODE)

    def test_call_passes_one_line_to_each_callback(self) -> None:
        for shell in False, True:
            with self.subTest(shell=shell):
                out: list[str] = []
                err: list[str] = []

                returncode = sproc.call(
                    command(CHILD, shell=shell), out.append, err.append, shell=shell
                )

                self.assert_output(out, err)
                self.assertEqual(returncode, EXIT_CODE)

    def test_run_preserves_text_and_returncode(self) -> None:
        for shell in False, True:
            with self.subTest(shell=shell):
                out, err, returncode = sproc.run(
                    command(CHILD, shell=shell), shell=shell
                )

                self.assert_output(out, err)
                self.assertEqual(returncode, EXIT_CODE)

    def test_chunk_mode_preserves_stream_text(self) -> None:
        out, err, returncode = sproc.run(command(CHILD, shell=False), by_lines=False)

        self.assertEqual(''.join(out), ''.join(STDOUT))
        self.assertEqual(''.join(err), ''.join(STDERR))
        self.assertEqual(returncode, EXIT_CODE)

    def test_log_preserves_stream_prefixes(self) -> None:
        lines: list[str] = []

        returncode = sproc.log(
            command(CHILD, shell=False), out='out: ', err='err: ', print=lines.append
        )

        self.assertCountEqual(
            lines,
            [
                *(f'out: {line}' for line in STDOUT),
                *(f'err: {line}' for line in STDERR),
            ],
        )
        self.assertEqual(returncode, EXIT_CODE)

    def test_async_helpers_return_none(self) -> None:
        for start in sproc.call_in_thread, sproc.call_async:
            with self.subTest(start=start.__name__):
                out: list[str] = []
                err: list[str] = []

                result = start(
                    command(ASYNC_CHILD, shell=False), out.append, err.append
                )

                self.assertIsNone(result)
                self.assertEqual(out, [])
                self.assertEqual(err, [])

    def test_sub_async_helpers_join_reader_threads(self) -> None:
        for method in 'call_in_thread', 'call_async':
            with self.subTest(method=method):
                out: list[str] = []
                err: list[str] = []
                sub = sproc.Sub(command(ASYNC_CHILD, shell=False))

                result = getattr(sub, method)(out.append, err.append)
                sub.join()

                self.assertIsNone(result)
                self.assertEqual(out, [])
                self.assertEqual(err, [])
                self.assertEqual(sub.returncode, 0)

    def test_configured_decoding_handles_invalid_utf8(self) -> None:
        out, err, returncode = sproc.run(
            command(INVALID_UTF8_CHILD, shell=False), encoding='utf-8', errors='replace'
        )

        self.assertEqual(out, ['�\n'])
        self.assertEqual(err, [])
        self.assertEqual(returncode, 0)

    def test_reader_error_records_invalid_utf8(self) -> None:
        sub = sproc.Sub(command(INVALID_UTF8_CHILD, shell=False))

        self.assertEqual(list(sub), [])
        self.assertIsInstance(sub.reader_error, UnicodeDecodeError)
        self.assertEqual(sub.returncode, 0)

    def test_lifecycle_properties_before_during_and_after_running(self) -> None:
        sub = sproc.Sub(command(RUNNING_CHILD, shell=False))

        self.assertFalse(sub.is_running)
        self.assertIsNone(sub.reader_error)
        sub.kill()

        iterator = iter(sub)
        self.assertEqual(next(iterator), (True, 'ready\n'))
        self.assertTrue(sub.is_running)
        self.assertEqual(list(iterator), [])
        self.assertFalse(sub.is_running)
        self.assertEqual(sub.returncode, 0)

    def test_start_returns_events_while_process_is_running(self) -> None:
        stream = sproc.start(command(RUNNING_CHILD, shell=False))

        self.assertTrue(stream.is_running)
        self.assertIsNone(stream.returncode)
        self.assertEqual(stream.wait(0.01), None)

        events = iter(stream)
        self.assertEqual(next(events), (True, 'ready\n'))
        self.assertTrue(stream.is_running)
        self.assertEqual(list(events), [])
        self.assertEqual(stream.wait(), 0)
        self.assertTrue(stream.join())
        self.assertEqual(stream.close(), 0)

    def test_start_keeps_concurrent_processes_separate(self) -> None:
        first = sproc.start(command("print('first')", shell=False))
        second = sproc.start(command("print('second')", shell=False))

        self.assertEqual(list(first), [(True, 'first\n')])
        self.assertEqual(list(second), [(True, 'second\n')])
        self.assertEqual(first.close(), 0)
        self.assertEqual(second.close(), 0)

    def test_start_records_reader_decoding_error(self) -> None:
        stream = sproc.start(command(INVALID_UTF8_CHILD, shell=False))

        self.assertEqual(list(stream), [])
        self.assertIsInstance(stream.reader_error, UnicodeDecodeError)
        self.assertEqual(stream.close(), 0)

    def test_start_decodes_configured_text(self) -> None:
        stream = sproc.start(command(LATIN_1_CHILD, shell=False), encoding='latin-1')

        self.assertEqual(list(stream), [(True, 'café\n')])
        self.assertIsNone(stream.reader_error)
        self.assertEqual(stream.close(), 0)

    def test_start_replaces_invalid_text(self) -> None:
        stream = sproc.start(
            command(INVALID_UTF8_CHILD, shell=False), encoding='utf-8', errors='replace'
        )

        self.assertEqual(list(stream), [(True, '�\n')])
        self.assertEqual(stream.close(), 0)

    def test_start_returns_binary_events(self) -> None:
        stream = sproc.start(command(INVALID_UTF8_CHILD, shell=False), encoding=None)

        self.assertEqual(list(stream), [(True, b'\xff\n')])
        self.assertIsNone(stream.reader_error)
        self.assertEqual(stream.close(), 0)

    def test_start_chunk_mode_delivers_before_process_exit(self) -> None:
        stream = sproc.start(
            command(CHUNK_CHILD, shell=False),
            by_lines=False,
            chunk_size=2,
            encoding=None,
        )

        events = iter(stream)
        self.assertEqual(next(events), (True, b'ab'))
        self.assertTrue(stream.is_running)
        self.assertEqual(list(events), [(True, b'cd'), (True, b'ef')])
        self.assertEqual(stream.close(), 0)

    def test_start_validates_chunk_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, 'positive chunk_size'):
            sproc.start(command(ASYNC_CHILD, shell=False), by_lines=False)
        with self.assertRaisesRegex(ValueError, 'requires by_lines=False'):
            sproc.start(command(ASYNC_CHILD, shell=False), chunk_size=1)

    def test_start_validates_text_encoding_before_launch(self) -> None:
        with self.assertRaises(LookupError):
            sproc.start(command(ASYNC_CHILD, shell=False), encoding='not-an-encoding')

    def test_start_bounded_queue_raises_after_draining_process(self) -> None:
        stream = sproc.start(
            command(OUTPUT_CHILD, shell=False), max_queue_size=1, overflow='raise'
        )

        self.assertEqual(stream.wait(), 0)
        with self.assertRaises(sproc.OutputQueueFullError):
            list(stream)
        self.assertIsInstance(stream.reader_error, sproc.OutputQueueFullError)
        self.assertEqual(stream.close(), 0)

    def test_start_requires_explicit_bounded_queue_policy(self) -> None:
        with self.assertRaisesRegex(ValueError, "overflow='raise'"):
            sproc.start(command(ASYNC_CHILD, shell=False), max_queue_size=1)
        with self.assertRaisesRegex(ValueError, 'overflow requires'):
            sproc.start(command(ASYNC_CHILD, shell=False), overflow='raise')

    def test_start_terminate_and_kill_are_idempotent(self) -> None:
        for method in 'terminate', 'kill':
            with self.subTest(method=method):
                stream = sproc.start(command(RUNNING_CHILD, shell=False))

                getattr(stream, method)()
                self.assertNotEqual(stream.wait(), 0)
                getattr(stream, method)()
                self.assertEqual(stream.close(), stream.returncode)

    def test_start_join_waits_for_inherited_output_descriptors(self) -> None:
        stream = sproc.start(command(INHERITING_CHILD, shell=False))

        self.assertEqual(stream.wait(), 0)
        self.assertFalse(stream.join(0.01))
        self.assertEqual(list(stream), [])
        self.assertTrue(stream.join())
        self.assertEqual(stream.close(), 0)
