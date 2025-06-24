from setuptools import setup, find_packages

setup(
    name="huion-keydial-mini-driver",
    version="0.1.0",
    description="User space driver for Huion Keydial Mini bluetooth device",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "bleak>=0.21.1",
        "evdev>=1.6.1",
        "pyudev>=0.24.1",
        "asyncio-mqtt>=0.13.0",
        "click>=8.1.7",
        "pyyaml>=6.0.1",
    ],
    entry_points={
        "console_scripts": [
            "huion-keydial-mini=huion_keydial_mini.main:main",
            "keydialctl=huion_keydial_mini.keydialctl:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
    keywords="huion keydial bluetooth hid driver uinput",
    url="https://github.com/your-username/huion-keydial-mini-uinput",
    project_urls={
        "Bug Reports": "https://github.com/your-username/huion-keydial-mini-uinput/issues",
        "Source": "https://github.com/your-username/huion-keydial-mini-uinput",
    },
)
