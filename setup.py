from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_reqs = fh.read().split()

setup(
    name="rt-server-client",
    version="0.3.0",
    packages=find_packages(),
    license="GPLv3",
    install_requires=install_reqs,
    description="Racktables Server client for automation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    scripts=[
        "scripts/system-info",
        "scripts/comment-edit",
        "scripts/get-bios-ident",
    ],
    url="https://github.com/rvojcik/rt-server-client",
    author="Robert Vojcik",
    author_email="robert@vojcik.net",
    keywords=['rtapi', 'racktables', 'racktables automation', 'automation','server','racktables-client', 'rt-server-client', 'rt-client'],
    classifiers=[
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
            "Operating System :: POSIX",
            "Operating System :: Unix",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3 :: Only",
            "Topic :: Documentation",
            "Topic :: System :: Systems Administration",
            "Topic :: Utilities",
            "Topic :: Database"
    ]
)


