from subprocessor import Sub
import unittest


class RunTest(unittest.TestCase):
    def setUp(self):
        self.lines = []

    def sub(self, cmd, **kwds):
        return Sub(cmd, **kwds).call(self.lines.append, self.lines.append)

    def test_simple(self):
        for shell in False, True:
            error = self.sub('ls', shell=shell)
            assert error == 0
            assert 'subprocessor.py\n' in self.lines
            assert len(self.lines) >= 10

    def test_error(self):
        for shell in False, True:
            self.lines.clear()
            error = self.sub('ls foo setup.py bar', shell=shell)
            assert error
            assert 'setup.py\n' in self.lines
            for f in 'foo', 'bar':
                assert sum(i.endswith(_NO_SUCH) for i in self.lines) == 2

    def test_log(self):
        for shell in False, True:
            self.lines.clear()

            sub = Sub('ls foo setup.py bar', shell=shell)
            error = sub.log(print=self.lines.append)
            assert error
            assert '  setup.py\n' in self.lines
            for f in 'foo', 'bar':
                assert sum(f in i for i in self.lines) == 1
            assert sum(i.startswith('*') for i in self.lines) == 2

    def test_run(self):
        for shell in False, True:
            sub = Sub('ls foo setup.py bar', shell=shell)
            out, err, error_code = sub.run()
            assert len(err) == 2
            assert error_code
            assert 'setup.py\n' in out
            for f in 'bar', 'foo':
                assert sum(f in i for i in err) == 1
            assert all(i.endswith(_NO_SUCH) for i in err)


_NO_SUCH = 'No such file or directory\n'
