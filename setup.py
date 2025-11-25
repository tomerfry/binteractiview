import os
import sys
import subprocess
from pathlib import Path
from setuptools import setup, find_packages


# Package metadata
NAME = "Binterview"
VERSION = "0.2.0"
DESCRIPTION = "Binary format interactive TUI viewer with PCAP analysis support"
AUTHOR = "Tomer Goldschmidt"

# Required packages
REQUIRED = [
    "textual>=0.40.0",
    "tree-sitter",
    "tree-sitter-python",
    "construct",
    "numpy",
]

# Optional dependencies
EXTRAS = {
    "bio": ["bio"],
    "full": ["bio", "scapy"],
}


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
    extras_require=EXTRAS,
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "bintv = bintv.main:main",
            "bintv-pcap = bintv.pcap_app:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: Utilities",
    ],
    python_requires=">=3.9",
)
