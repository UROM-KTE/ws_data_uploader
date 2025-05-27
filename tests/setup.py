from setuptools import setup, find_packages

setup(
    name="weather-station-collector",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests~=2.32.3",
        "schedule~=1.2.2",
        "psycopg2-binary~=2.9.10",
    ],
    extras_require={
        "windows": ["pywin32>=310"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "mypy>=1.3.0",
            "types-psycopg2",
            "types-requests",
            "types-pywin32",
        ],
    },
    entry_points={
        'console_scripts': [
            'weather-collector=main:main',
        ],
    },
)
