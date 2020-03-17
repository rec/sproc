import subprocessor
import os
import unittest


class RunTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        self.lines = []

    def sub(self, cmd):
        return subprocessor.Runner(cmd).communicate(self.lines.append)

    def test_simple(self):
        error = self.sub('ls')
        assert error == 0
        assert 'subprocessor.py' in self.lines
        assert len(self.lines) >= 10

    def test_error(self):
        error = self.sub('ls foo setup.py bar')
        assert error
        assert 'setup.py' in self.lines
        no_such = 'No such file or directory'
        assert sum(no_such in i for i in self.lines) == 2
