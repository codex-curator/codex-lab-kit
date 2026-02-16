from setuptools import setup, find_packages

setup(
    name="codex-lab-kit",
    version="1.0.0",
    description="Golden Codex Lab Validation Kit — Standardized experiment protocols for robotic manipulation research",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="iAeternum / Metavolve Labs",
    author_email="research@iaeternum.ai",
    url="https://github.com/codex-curator/codex-lab-kit",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.24",
    ],
    extras_require={
        "core": ["gcp-robotics>=2.0"],  # Private core — available to approved partners
        "analysis": ["matplotlib>=3.7", "scipy>=1.10"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Robotics",
    ],
    project_urls={
        "Homepage": "https://iaeternum.ai/robotics",
        "Bug Tracker": "https://github.com/codex-curator/codex-lab-kit/issues",
        "Documentation": "https://github.com/codex-curator/codex-lab-kit/tree/main/docs",
    },
)
