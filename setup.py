import subprocessor
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
        name='subprocessor',
        version=subprocessor.__version__,
        author='Tom Ritchford',
        author_email='tom@swirly.com',
        url='https://github.com/rec/subprocessor',
        tests_require=['pytest'],
        py_modules=['subprocessor'],
        description='Run a subprocess with callbacks',
        long_description=open('README.rst').read(),
        license='MIT',
        classifiers=_classifiers,
        keywords=['backups'],
    )
