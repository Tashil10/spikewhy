from setuptools import setup, find_packages

setup(
    name="spikewhy",
    version="0.1.0",
    description="Trace cloud cost spikes back to the PR that caused them",
    author="Tashil",
    url="https://github.com/Tashil10/spikewhy",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "spikewhy=spikewhy.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
