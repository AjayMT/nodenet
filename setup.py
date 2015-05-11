#!/usr/bin/env python

from setuptools import setup

setup(
    name='nodenet',
    version='0.0.3',
    description='an asynchronous node-based UDP networking library',
    author='Ajay MT',
    author_email='ajaymt@icloud.com',
    url='http://github.com/AjayMT/nodenet',
    download_url='https://github.com/AjayMT/nodenet/tarball/v0.0.3',
    keywords='node network UDP asynchronous',
    py_modules=['nodenet'],
    requires=[
        'pyuv (>1.0.0, <2.0.0)',
        'emitter (>=0.0.5)'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
    ]
)
