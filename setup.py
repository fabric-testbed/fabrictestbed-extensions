import setuptools

from fabrictestbed_extensions import __VERSION__

VERSION = __VERSION__

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    requirements = fh.read()

setuptools.setup(
    name='fabrictestbed',
    version=VERSION,
    author="Paul Ruth",
    author_email="pruth@renci.org",
    description="FABRIC Python Client Library and CLI Extensions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fabric-testbed/fabrictestbed-extensions",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
                  "Programming Language :: Python :: 3",
                  "License :: OSI Approved :: MIT License",
                  "Operating System :: OS Independent",
              ],
    python_requires='>=3.9',
)



