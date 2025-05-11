from setuptools import setup, find_packages

setup(
    name="obscopilot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "twitchio",
        "sqlalchemy",
        "toml",
        "python-dotenv",
    ],
    entry_points={
        'console_scripts': [
            'obscopilot=obscopilot.main:main',
        ],
    },
) 