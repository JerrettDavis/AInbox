#!/usr/bin/env python3
"""Setup script for AInbox package."""

from setuptools import setup, find_packages

setup(
    name="ainbox",
    version="0.1.0",
    description="Filesystem-based async mailbox for coding agents",
    author="Jerrett Davis",
    url="https://github.com/JerrettDavis/AInbox",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mailbox=ainbox.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
