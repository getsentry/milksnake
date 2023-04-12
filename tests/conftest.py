import os
import sys
import uuid
import json
import atexit
import pytest
import shutil
import tempfile
import subprocess


root = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))


EVAL_HOOK = '''
import sys
import json

ns = {}
code = compile(sys.stdin.read(), '<stdin>', 'exec')
eval(code, ns)
print(json.dumps(ns['execute']()))
'''


class VirtualEnv(object):

    def __init__(self, path):
        self.path = path

    def spawn(self, executable, args=None, **kwargs):
        bin_dir = 'bin'
        if sys.platform == 'win32' and not executable.endswith('.exe'):
            bin_dir = 'Scripts'
        return subprocess.Popen([os.path.join(self.path, bin_dir, executable)] +
                                list(args or ()), **kwargs)

    def run(self, executable, args=None):
        rv = self.spawn(executable, args).wait()
        if rv != 0:
            raise RuntimeError('Program exited with %d' % rv)

    def eval(self, code):
        proc = self.spawn('python', ['-c', EVAL_HOOK],
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE)
        stdout = proc.communicate(code.encode('utf-8'))[0]
        rv = proc.wait()
        if rv != 0:
            raise RuntimeError('Interpreter exited with %d' % rv)
        return json.loads(stdout)


@pytest.fixture
def virtualenv():
    path = os.path.join(tempfile.gettempdir(), '.' + str(uuid.uuid4()))

    def _remove():
        try:
            shutil.rmtree(path)
        except Exception:
            pass

    atexit.register(_remove)

    subprocess.Popen(['virtualenv', path]).wait()
    try:
        venv = VirtualEnv(path)
        venv.run('python', ['-m', 'pip', 'install', '--editable', root])
        yield venv
    finally:
        _remove()
