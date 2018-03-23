import os


def test_example_dev_run(virtualenv):
    pkg = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       'res', 'minimal'))
    virtualenv.run('pip', ['install', '-v', '--editable', pkg])
    virtualenv.eval('''if 1:
        from example import test
        def execute():
            assert test() == (0.0, 0.0)
    ''')
