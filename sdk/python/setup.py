#!/usr/bin/env python3
"""
setup.py — MAGNATRIX Python SDK Package
pip install -e sdk/python/
"""
from setuptools import setup, find_packages

setup(
    name="magnatrix-sdk",
    version="0.1.0",
    description="MAGNATRIX Agentic OS Python SDK",
    author="Leonard Treas",
    author_email="leonard@magnatrix.io",
    url="https://github.com/Magnatrix-Lab/MAGNATRIX-OS",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": ["pytest", "mypy", "black"],
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
        "Programming Language :: Python :: 3.12",
    ],
)
