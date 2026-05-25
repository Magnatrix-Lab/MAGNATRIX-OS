"""
MAGNATRIX Agentic OS
═══════════════════════
Setup script untuk instalasi sebagai Python package.
"""

from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))

# Auto-version from CHANGELOG or fallback
version = "0.7.1"
changelog = os.path.join(here, "CHANGELOG.md")
if os.path.exists(changelog):
    with open(changelog, encoding="utf-8") as f:
        for line in f:
            if line.startswith("## v"):
                try:
                    version = line.split()[1].strip()
                    break
                except Exception:
                    pass

with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(here, "requirements.txt"), encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="magnatrix-os",
    version=version,
    description="MAGNATRIX Agentic OS — Open-source AI Operating System evolving toward AGI and Super AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Magnatrix-Lab/MAGNATRIX-OS",
    author="Leonard Treas & MAGNATRIX Contributors",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Operating System",
    ],
    keywords="agentic ai agi super-ai os autonomous agent swarm uncensored",
    packages=find_packages(exclude=["tests", "benchmarks", "docs", "scripts"]),
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "magnatrix=magnatrix_cli:main",
            "magnatrix-server=magnatrix_server:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
