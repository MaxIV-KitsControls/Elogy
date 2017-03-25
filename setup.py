from setuptools import setup

setup(
    name='elogy',
    packages=['elogy'],
    include_package_data=True,
    install_requires=[
        'flask', 'peewee', 'blinker', 'lxml', 'pillow', 'dateutils'
    ],
)
