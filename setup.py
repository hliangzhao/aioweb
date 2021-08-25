#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages


setup(
    name='aioweb',
    version='0.0.1',
    description=(
        'A lightweight async web framework'
    ),
    author='Hailiang Zhao',
    author_email='hliangzhao@zju.edu.cn',
    maintainer='Hailiang Zhao',
    license='MIT License',
    packages=find_packages(),
    platforms=["all"],
    url='https://github.com/hliangzhao/aioweb',
    classifiers=[
        'Development Status :: 1 - Beta',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries'
    ],
    install_requires=[
        'numpy',
        'pandas',
    ]
)