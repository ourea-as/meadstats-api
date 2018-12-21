from setuptools import setup

setup(
    name='Meadstats API',
    packages=['app'],
    include_package_data=True,
    install_requires=[
        'flask',
    ],
)
