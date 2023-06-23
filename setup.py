from setuptools import setup

setup(
    name="Meadstats API",
    packages=["meadstatsapi"],
    include_package_data=True,
    install_requires=[
        "flask",
    ],
)
