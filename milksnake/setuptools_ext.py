import os
import sys
import shutil
import subprocess

from distutils import log
from distutils.command.build_py import build_py
from distutils.command.build_ext import build_ext

from cffi import FFI
from cffi import recompiler as cffi_recompiler

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    bdist_wheel = None

here = os.path.abspath(os.path.dirname(__file__))

MODULE_PY = u'''# auto-generated file
__all__ = ['lib', 'ffi']

import os
from %(cffi_module_path)s import ffi

lib = ffi.dlopen(os.path.join(os.path.dirname(__file__), %(lib_filename)r), %(rtld_flags)r)
del os
'''


class Spec(object):

    def __init__(self, dist):
        self.dist = dist
        self.builds = []

        self._dist_build_funcs = []

    def add_build_step(self, build_step):
        self.builds.append(build_step)
        return build_step

    def prepare_build(self):
        for build_step in self.builds:
            build_step.prepare_build()

    def add_external_build(self, *args, **kwargs):
        return self.add_build_step(ExternalBuildStep(self, *args, **kwargs))

    def add_cffi_module(self, *args, **kwargs):
        return self.add_build_step(CffiModuleBuildStep(self, *args, **kwargs))

    def add_build_func(self, func, module_base=None):
        """Registers a function to be called with the build."""
        patched = bool(self._dist_build_funcs)
        self._dist_build_funcs.append((func, module_base))
        if not patched:
            self._patch_build_commands()

    def _patch_build_commands(self):
        base_build_ext = self.dist.cmdclass.get('build_ext', build_ext)
        base_build_py = self.dist.cmdclass.get('build_py', build_py)
        spec = self

        class MilksnakeBuildPy(base_build_py):
            def run(self):
                base_build_py.run(self)
                for func, module_base in spec._dist_build_funcs:
                    base_path = None
                    if module_base is not None:
                        base_path = os.path.join(
                            self.build_lib, *module_base.split('.'))
                    func(base_path=base_path, inplace=False)

        class MilksnakeBuildExt(base_build_ext):
            def run(self):
                base_build_ext.run(self)
                if self.inplace:
                    build_py = self.get_finalized_command('build_py')
                    for func, module_base in spec._dist_build_funcs:
                        base_path = None
                        if module_base is not None:
                            base_path = build_py.get_package_dir(
                                module_base)
                        func(base_path=base_path, inplace=True)

        self.dist.cmdclass['build_py'] = MilksnakeBuildPy
        self.dist.cmdclass['build_ext'] = MilksnakeBuildExt


class BuildStep(object):

    def __init__(self, spec, path=None):
        self.spec = spec
        self.path = path

    def prepare_build(self):
        raise NotImplementedError('no build step implemented')


class ExternalBuildStep(BuildStep):

    def __init__(self, spec, cmd=None, cwd=None, path=None, env=None):
        BuildStep.__init__(self, spec, path=path)
        self.cmd = cmd
        self.cwd = cwd
        self.path = path
        self.env = env

    def find_dylib(self, name, in_path=None):
        path = self.path or '.'
        if in_path is not None:
            path = os.path.join(path, *in_path.split('/'))

        to_find = None
        if sys.platform == 'darwin':
            to_find = 'lib%s.dylib' % name
        elif sys.platform == 'win32':
            to_find = '%s.dll' % name
        else:
            to_find = 'lib%s.so' % name

        for filename in os.listdir(path):
            if filename == to_find:
                return os.path.join(path, filename)

        raise LookupError('dylib %r not found' % name)

    def find_header(self, name, in_path=None):
        path = self.path or '.'
        if in_path is not None:
            path = os.path.join(path, *in_path.split('/'))
        for filename in os.listdir(path):
            if filename == name:
                return os.path.join(path, filename)

        raise LookupError('header %r not found' % name)

    def prepare_build(self):
        def build(**extra):
            cwd = self.cwd or self.path
            env = dict(os.environ)
            if self.env is not None:
                env.update(self.env)
            rv = subprocess.Popen(self.cmd, cwd=cwd, env=env).wait()
            if rv != 0:
                sys.exit(rv)
        self.spec.add_build_func(build)


def get_rtld_flags(flags):
    if sys.platform == "win32":
        return 0

    ffi = FFI()
    if not flags:
        return ffi.RTLD_NOW

    rv = 0
    for flag in flags:
        if flag.startswith('RTLD_'):
            flag = flag[5:]
        rv |= getattr(ffi, 'RTLD_' + flag.upper())
    return rv


class CffiModuleBuildStep(BuildStep):

    def __init__(self, spec, module_path, dylib=None, header_filename=None,
                 header_source=None, header_strip_directives=True,
                 path=None, rtld_flags=None):
        BuildStep.__init__(self, spec, path=path)
        self.module_path = module_path
        self.dylib = dylib
        self.header_filename = header_filename
        self.header_source = header_source
        self.header_strip_directives = header_strip_directives
        self.rtld_flags = get_rtld_flags(rtld_flags)

        parts = self.module_path.rsplit('.', 1)
        self.module_base = parts[0]
        self.name = parts[-1]

        genbase = '%s._%s' % (parts[0], parts[1].lstrip('_'))
        self.cffi_module_path = '%s__ffi' % genbase

        from distutils.sysconfig import get_config_var

        if sys.platform == 'darwin':
            plat_ext = ".dylib"
        elif sys.platform == 'win32':
            plat_ext = ".dll"
        else:
            plat_ext = ".so"
        ext = get_config_var('EXT_SUFFIX') or \
            get_config_var('SHLIB_SUFFIX') or \
            get_config_var('SO') or plat_ext

        self.lib_filename = '%s__lib%s' % (genbase.split('.')[-1], ext)

    def get_header_source(self):
        if self.header_source is not None:
            return self.header_source
        if callable(self.header_filename):
            fn = self.header_filename()
        else:
            fn = self.header_filename

        with open(fn, 'rb') as f:
            return f.read()

    def prepare_build(self):
        dist = self.spec.dist
        if dist.ext_modules is None:
            dist.ext_modules = []

        def make_ffi():
            from milksnake.ffi import make_ffi
            return make_ffi(self.module_path,
                            self.get_header_source(),
                            strip_directives=self.header_strip_directives)

        def build_cffi(base_path, **extra):
            # dylib
            dylib = self.dylib()
            if callable(dylib):
                dylib = dylib()
            log.info('copying dylib %s', os.path.basename(dylib))
            shutil.copy2(dylib, os.path.join(base_path, self.lib_filename))

            # generate cffi module
            ffi = make_ffi()
            log.info('generating cffi module for %r' % self.module_path)
            py_file = os.path.join(
                base_path, self.cffi_module_path.split('.')[-1]) + '.py'
            updated = cffi_recompiler.make_py_source(
                ffi, self.cffi_module_path, py_file)
            if not updated:
                log.info('already up-to-date')

            # wrapper
            log.info('generating wrapper for %r' % self.module_path)
            with open(os.path.join(base_path, self.name + '.py'), 'wb') as f:
                f.write((MODULE_PY % {
                    'cffi_module_path': self.cffi_module_path,
                    'lib_filename': self.lib_filename,
                    'rtld_flags': self.rtld_flags,
                }).encode('utf-8'))
        self.spec.add_build_func(build_cffi, module_base=self.module_base)


def milksnake_universal(dist, attr, value):
    """Enables or disables universal wheel support."""
    patch_universal_wheel(dist)
    dist.milksnake_universal = value


def patch_universal_wheel(dist):
    value = getattr(dist, 'milksnake_universal', None)
    if value is None:
        dist.milksnake_universal = True

    base_bdist_wheel = dist.cmdclass.get('bdist_wheel', bdist_wheel)

    if base_bdist_wheel is None:
        return

    class MilksnakeBdistWheel(base_bdist_wheel):
        def get_tag(self):
            rv = base_bdist_wheel.get_tag(self)
            if not dist.milksnake_universal:
                return rv
            return ('py2.py3', 'none',) + rv[2:]

    dist.cmdclass['bdist_wheel'] = MilksnakeBdistWheel


def patch_distutils_build(dist):
    """Trick wheel and other systems into assuming
    our library has binary extensions

    See also https://github.com/pypa/distutils/pull/43
    """
    from distutils.command import build as _build

    class build(_build.build, object):
        def finalize_options(self):
            super(build, self).finalize_options()
            if self.distribution.has_ext_modules():
                self.build_lib = self.build_platlib
            else:
                self.build_lib = self.build_purelib

    _build.build = build

    orig_has_ext_modules = dist.has_ext_modules
    dist.has_ext_modules = lambda: (
        orig_has_ext_modules() or bool(dist.milksnake_tasks)
    )


def milksnake_tasks(dist, attr, value):
    """Registers task callbacks."""
    patch_distutils_build(dist)
    patch_universal_wheel(dist)

    spec = Spec(dist)
    for callback in value or ():
        callback(spec)

    spec.prepare_build()
