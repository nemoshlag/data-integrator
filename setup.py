from setuptools import setup, find_packages

setup(
    name="hospital-monitor",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.26.137",
        "aws-lambda-powertools>=2.15.0",
        "pydantic>=1.10.7",
        "python-dateutil>=2.8.2",
        "pandas>=2.0.1",
        "requests>=2.31.0",
        "websockets>=11.0.3",
        "structlog>=23.1.0"
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="Hospital patient monitoring system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="healthcare, monitoring, aws, serverless",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)