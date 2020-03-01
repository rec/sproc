from run_subprocess import run_to_list
import os
import unittest


class RunTest(unittest.TestCase):
    def setUp(self):
        os.chdir(os.path.dirname(os.path.dirname(__file__)))

    def test_simple(self):
        error, lines = run_to_list('ls')
        assert error == 0
        assert 'run_subprocess.py' in lines
        assert len(lines) >= 10

    def test_error(self):
        error, lines = run_to_list('ls foo setup.py bar')
        assert error
        assert 'setup.py' in lines
        no_such = 'No such file or directory'
        assert sum(no_such in i for i in lines) == 2
