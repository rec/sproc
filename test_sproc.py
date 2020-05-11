import doc_sproc
from readme_renderer.rst import render
import sproc
import unittest


class RunTest(unittest.TestCase):
    def setUp(self):
        self.lines = []

    def sub(self, cmd, **kwds):
        return sproc.call(cmd, self.lines.append, self.lines.append, **kwds)

    def test_simple(self):
        for shell in False, True:
            self.lines.clear()
            error = self.sub('ls', shell=shell)

            assert error == 0
            assert 'sproc.py\n' in self.lines
            assert len(self.lines) >= 10

    def test_error(self):
        for shell in False, True:
            self.lines.clear()
            error = self.sub('ls foo setup.py bar', shell=shell)

            assert error
            assert 'setup.py\n' in self.lines

            for _ in 'foo', 'bar':
                assert sum(i.endswith(_NO_SUCH) for i in self.lines) == 2

    def test_log(self):
        cmd = 'ls foo setup.py bar'
        for shell in False, True:
            self.lines.clear()
            error = sproc.log(cmd, shell=shell, print=self.lines.append)

            assert error
            assert len(self.lines) == 3
            assert '  setup.py\n' in self.lines

            for f in 'foo', 'bar':
                assert sum(f in i for i in self.lines) == 1

            assert sum(i.startswith('! ') for i in self.lines) == 2

    def test_run(self):
        cmd = 'ls foo setup.py bar'
        for shell in False, True:
            out, err, error_code = sproc.run(cmd, shell=shell)

            assert len(err) == 2
            assert error_code
            assert 'setup.py\n' in out

            for f in 'bar', 'foo':
                assert sum(f in i for i in err) == 1

            assert all(i.endswith(_NO_SUCH) for i in err)

    def test_make_doc(self):
        actual = doc_sproc.make_doc()
        with open('README.rst') as fp:
            assert actual == fp.read()

    def test_readme_format(self):
        with open('README.rst') as fp:
            assert render(fp.read())

    def test_async(self):
        for shell in False, True:
            lines, errors = [], []
            sub = sproc.Sub('ls setup.py MISSING', shell=shell)
            sub.call_async(lines.append, errors.append)
            sub.join()
            assert sub.returncode != 0

            assert 'setup.py\n' in lines
            assert len(lines) == 1
            assert len(errors) == 1


_NO_SUCH = 'No such file or directory\n'
