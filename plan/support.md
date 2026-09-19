# Current support matrix

This matrix records what has been verified, not a promise that unverified
platforms cannot work.

| Area | Current position |
| --- | --- |
| Python | Compatibility tests run on CPython 3.10.x only. The package metadata continues to require Python 3.10 or later. |
| macOS | The Phase 0 test suite is verified here. |
| Linux | Release-only GitHub Actions validation is configured; the first published-release result is pending. |
| Windows | Release-only GitHub Actions validation is configured; the first published-release result is pending. |
| String commands | Verified with the current POSIX `shlex` normalization on macOS. |
| Sequence commands | Verified on macOS without a shell. |
| `shell=True` | Verified only with the macOS shell. Its Windows command semantics are not yet validated. |
| Text output | `ProcessStream` defaults to UTF-8 text with strict decoding and supports explicit `encoding` and `errors` settings. |
| Binary output | `ProcessStream(encoding=None)` yields bytes events. Legacy helpers remain text-only. |

The Phase 0 suite uses `sys.executable` child scripts instead of platform shell
utilities. The release-only GitHub Actions workflow runs it on macOS, Linux,
and Windows with CPython 3.10 when a release is published.
