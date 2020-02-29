import run_subprocess
from setuptools import setup

_classifiers = [
    'Development Status :: 4 - Beta',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
]

if __name__ == '__main__':
    setup(
        name='run_subprocess',
        version=run_subprocess.__version__,
        author='Tom Ritchford',
        author_email='tom@swirly.com',
        url='https://github.com/rec/run_subprocess',
        tests_require=['pytest'],
        py_modules=['run_subprocess'],
        description='Run a subprocess with callbacks',
        long_description=open('README.md').read(),
        license='MIT',
        classifiers=_classifiers,
        keywords=['backups'],
        # scripts=['run_subprocess.py'],
    )
