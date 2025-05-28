from setuptools import setup, find_packages

setup(
    name="ws_data_uploader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "psycopg2-binary>=2.9.10",
        "pywin32>=310; platform_system=='Windows'",
        "requests>=2.32.3",
        "schedule>=1.2.2",
        "setuptools>=80.8.0",
    ],
    extras_require={
        "dev": [
            "black>=25.1.0",
            "build>=1.2.2",
            "flake8>=7.2.0",
            "mypy>=1.15.0",
            "pyinstaller>=6.13.0",
            "pytest>=8.0.0,<8.3.0",
            "pytest-cov>=6.1.1",
            "types-psycopg2>=2.9.21.20250516",
            "types-requests>=2.32.0.20250515",
            "types-pywin32>=310.0.0.20250516",
            "wheel>=0.40.0,<0.46.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ws_data_uploader=weather_station.main:main",
        ],
    },
    python_requires=">=3.12,<3.13",
    author="Attila Ferenc",
    author_email="attila.ferenc.dev@gmail.com",
    description="A robust, cross-platform application for collecting, storing, and managing weather station data created by idokep.hu",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/UROM-KTE/ws_data_uploader",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
    ],
)
