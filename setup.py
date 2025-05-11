from setuptools import setup, find_packages

# Define different requirement sets
install_requires = [
    "PyQt6>=6.4.0",
    "twitchio>=2.6.0",
    "sqlalchemy>=2.0.0",
    "toml>=0.10.2",
    "python-dotenv>=1.0.0",
    "obs-websocket-py>=1.0",
    "openai>=1.0.0",
    "google-generativeai>=0.3.0",
    "pillow>=10.0.0",
    "requests>=2.0.0",
    "pyyaml>=6.0",
]

test_requires = [
    "pytest>=7.0.0",
    "pytest-qt>=4.2.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.10.0",
]

dev_requires = [
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.3.0",
    "isort>=5.12.0",
] + test_requires

setup(
    name="obscopilot",
    version="0.1.0",
    description="Twitch live assistant with OBS integration and workflow automation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="OBSCopilot Team",
    author_email="info@obscopilot.com",
    url="https://github.com/justedave0/obscopilot",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=install_requires,
    extras_require={
        "test": test_requires,
        "dev": dev_requires,
    },
    entry_points={
        'console_scripts': [
            'obscopilot=obscopilot.main:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Communications :: Chat",
    ],
    license="MIT",
    keywords="obs twitch streaming automation workflow",
    project_urls={
        "Documentation": "http://obscopilot.live/",
        "Source": "https://github.com/justedave0/obscopilot",
        "Bug Reports": "https://github.com/justedave0/obscopilot/issues",
    },
) 