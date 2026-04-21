#!/usr/bin/env python3
"""Setup script for AInbox package."""

from pathlib import Path
import re

from setuptools import find_packages, setup


def read_version() -> str:
    init_py = Path(__file__).resolve().parent / "ainbox" / "__init__.py"
    match = re.search(
        r'^__version__\s*=\s*"([^"]+)"',
        init_py.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError(f"Unable to determine package version from {init_py}")
    return match.group(1)

setup(
    name="ainbox",
    version=read_version(),
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
