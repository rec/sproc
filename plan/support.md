# Current support matrix

This matrix records what has been verified, not a promise that unverified
platforms cannot work.

| Area | Current position |
| --- | --- |
| Python | Compatibility tests run on CPython 3.10.x only. The package metadata continues to require Python 3.10 or later. |
| macOS | The Phase 0 test suite is verified here. |
| Linux | Compatibility validation is deferred to the final release phase. |
| Windows | Compatibility validation is deferred to the final release phase. |
| String commands | Verified with the current POSIX `shlex` normalization on macOS. |
| Sequence commands | Verified on macOS without a shell. |
| `shell=True` | Verified only with the macOS shell. Its Windows command semantics are not yet validated. |
| Text output | Default behavior is UTF-8 text with strict decoding. A configured `encoding='utf-8', errors='replace'` path is covered for invalid bytes. |
| Binary output | No public binary-output contract exists yet. |

The Phase 0 suite uses `sys.executable` child scripts instead of platform shell
utilities, so it can become the portability baseline when Linux and Windows
testing is funded at the final release stage.
