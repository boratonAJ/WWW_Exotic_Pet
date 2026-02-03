from setuptools import setup, find_packages

setup(
    name="project_name",
    version="0.1.0",
    description="Data science project",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        # Add core dependencies here
    ],
)
