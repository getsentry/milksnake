import os


def test_example_dev_run(virtualenv):
    pkg = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       'res', 'minimal'))
    virtualenv.run('python', ['-m', 'pip', 'install', '-v', '--editable', pkg])
    virtualenv.eval('''if 1:
        from example import test
        def execute():
            assert test() == (0.0, 0.0)
    ''')


def test_example_nested_dev_run(virtualenv):
    pkg = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       'res', 'nested'))
    virtualenv.run('python', ['-m', 'pip', 'install', '-v', '--editable', pkg])
    virtualenv.eval('''if 1:
        from example.nested import test
        def execute():
            assert test() == (0.0, 0.0)
    ''')
