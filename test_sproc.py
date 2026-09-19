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
