from subprocessor import Sub
import inspect
import subprocessor as sub

README_FILE = 'README.rst'
_, *ALL = sub.__all__

assert _ == 'Sub'


def main():
    with open(README_FILE, 'w') as fp:
        fp.write(make_doc())


def make_doc():
    def header(s, c='-'):
        return '%s\n%s' % (s, c * (len(s) + s.count('`')))

    def sig(name, thing):
        return '`%s%s`' % (name, str(inspect.signature(thing)))

    def indent(s, indent='    '):
        for i in s.splitlines():
            yield indent + i if i.strip() else i
        yield ''

    def bold(s, c='**'):
        return c + s.replace(c, '\\' + c) + c

    def sub_class():
        yield from (sub.__doc__, '***', 'API', '***', '')
        yield header('Methods on `class subprocessor.Sub:`', '=')
        yield ''
        yield header('`Sub.__init__(self, cmd, **kwds)`')
        yield from indent(Sub.__doc__)

        for name in ['__iter__'] + ALL:
            method = getattr(Sub, name)
            yield header(sig('Sub.' + name, method))
            yield from indent(method.__doc__)

    def apis():
        yield from sub_class()
        yield ''
        yield header('Functions', '=')

        for name in ALL:
            function = getattr(sub, name)
            yield ''
            yield header(sig('subprocessor.' + name, function))
            yield from indent(function.__doc__)

    return '\n'.join(apis()).strip().replace('`', '``')


if __name__ == '__main__':
    main()
