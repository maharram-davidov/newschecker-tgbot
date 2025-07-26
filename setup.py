#!/usr/bin/env python3
"""
Setup configuration for NewsChecker package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
else:
    requirements = []

setup(
    name="newschecker",
    version="1.0.0",
    author="NewsChecker Team",
    author_email="info@newschecker.az",
    description="AI-powered news verification system for Azerbaijani content",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/newschecker/newschecker",
    project_urls={
        "Bug Reports": "https://github.com/newschecker/newschecker/issues",
        "Source": "https://github.com/newschecker/newschecker",
        "Documentation": "https://newschecker.readthedocs.io/",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Communications :: Chat",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Natural Language :: Azerbaijani",
        "Natural Language :: English",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
            "isort>=5.12",
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
            "sentry-sdk>=1.32.0",
            "structlog>=23.0",
        ],
        "production": [
            "gunicorn>=21.0",
            "uvicorn>=0.23.0",
            "redis>=4.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "newschecker=newschecker.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "newschecker": [
            "templates/*.html",
            "static/**/*",
        ],
    },
    zip_safe=False,
    keywords=[
        "news",
        "verification",
        "fact-checking",
        "ai",
        "telegram",
        "bot",
        "azerbaijan",
        "misinformation",
        "credibility",
        "analysis",
    ],
) 