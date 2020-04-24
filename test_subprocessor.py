import subprocessor
import unittest


class RunTest(unittest.TestCase):
    def setUp(self):
        self.lines = []

    def sub(self, cmd):
        return subprocessor.call(cmd, self.lines.append, self.lines.append)

    def test_simple(self):
        error = self.sub('ls')
        assert error == 0
        assert 'subprocessor.py' in self.lines
        assert len(self.lines) >= 10

    def test_error(self):
        error = self.sub('ls foo setup.py bar')
        assert error
        assert 'setup.py' in self.lines
        for f in 'foo', 'bar':
            assert sum(i.endswith(_NO_SUCH) for i in self.lines) == 2

    def test_log(self):
        error = subprocessor.log(
            'ls foo setup.py bar', print=self.lines.append
        )
        assert error
        assert '  setup.py' in self.lines
        for f in 'foo', 'bar':
            assert sum(f in i for i in self.lines) == 1
            assert sum(i.startswith('*') for i in self.lines) == 2

    def test_run(self):
        out, err, error_code = subprocessor.run('ls foo setup.py bar')
        assert error_code
        assert 'setup.py' in out
        assert len(err) == 2
        for f in 'bar', 'foo':
            assert sum(f in i for i in err) == 1
        assert all(i.endswith(_NO_SUCH) for i in err)


_NO_SUCH = 'No such file or directory'
