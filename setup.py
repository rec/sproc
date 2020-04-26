from setuptools import setup
import sproc

_classifiers = [
    'Development Status :: 5 - Production/Stable',
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
        name='sproc',
        version=sproc.__version__,
        author='Tom Ritchford',
        author_email='tom@swirly.com',
        url='https://github.com/rec/sproc',
        tests_require=['pytest'],
        py_modules=['sproc'],
        description='Run a subprocess with callbacks',
        long_description=open('README.rst').read(),
        license='MIT',
        classifiers=_classifiers,
        keywords=['backups'],
    )
