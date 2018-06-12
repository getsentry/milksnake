from setuptools import setup
from setuptools.dist import Distribution

with open('README.md', 'rb') as f:
    readme = f.read().decode('utf-8')

setup(
    name='milksnake',
    version='0.1.5',
    author='Armin Ronacher',
    author_email='armin.ronacher@active-4.com',
    license='Apache License 2.0',
    packages=['milksnake'],
    package_data={
        'milksnake': ['empty.c'],
    },
    description='A python library that extends setuptools for binary extensions.',
    long_description=readme,
    long_description_content_type='text/markdown',
    zip_safe=False,
    platforms='any',
    install_requires=[
        'cffi>=1.6.0',
    ],
    setup_requires=[
        'cffi>=1.6.0',
    ],
    entry_points={
        'distutils.setup_keywords': [
            'milksnake_tasks = milksnake.setuptools_ext:milksnake_tasks',
            'milksnake_universal = milksnake.setuptools_ext:milksnake_universal',
        ],
    },
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
    ],
)
