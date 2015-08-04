import os
from setuptools import setup


version_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 'doctor', '_version.py')
with open(version_file_path, 'r') as version_file:
    exec(compile(version_file.read(), version_file_path, 'exec'))

setup(
    name=__name__,
    version=__version__,  # noqa -- flake8 should ignore this line
    description='The doctor is in.',
    url='https://github.com/noonat/doctor',
    author='Nathan Ostgard',
    author_email='no@nathanostgard.com',
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    packages=['doctor'],
    install_requires=[
        'jsonschema>=2.5.1,<3.0.0',
        'six>=1.9.0,<2.0.0',
    ],
    extras_require={
        'docs': [
            'sphinx',
        ],
        'tests': [
            'flake8',
            'mock',
            'pytest',
            'pytest-cov',
        ],
    }
)
