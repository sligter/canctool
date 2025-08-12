#!/usr/bin/env python3
"""
Setup script for CancTool - LLM Tool Call Wrapper Service

This setup.py is provided for backward compatibility.
The primary build configuration is in pyproject.toml.
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# 读取版本信息
def get_version():
    version_file = os.path.join("canctool", "__init__.py")
    with open(version_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "1.0.0"

setup(
    name="canctool",
    version=get_version(),
    author="CancTool Team",
    author_email="support@canctool.com",
    description="LLM Tool Call Wrapper Service with multi-provider support",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/canctool/canctool",
    project_urls={
        "Bug Tracker": "https://github.com/canctool/canctool/issues",
        "Documentation": "https://canctool.readthedocs.io",
        "Source Code": "https://github.com/canctool/canctool",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8.1",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "httpx>=0.25.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "isort>=5.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "canctool=main:main",
            "canctool-server=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="llm openai tool-calling api wrapper multi-provider",
)
