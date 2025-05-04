import os
import sys
import subprocess
from pathlib import Path
from setuptools import setup, find_packages


# Package metadata
NAME = "Binterview"
VERSION = "0.1.0"
DESCRIPTION = "Binary format interactive TUI based viewer"
AUTHOR = "Tomer Goldschmidt"

# Required packages
REQUIRED = [
    "textual",
    "construct",
    "numpy"
]


# Read the README file
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = DESCRIPTION


setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    packages=find_packages(),
    install_requires=REQUIRED,
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "bintv = bintv.main:main"
        ]
    }
)
