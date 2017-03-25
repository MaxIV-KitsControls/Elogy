from setuptools import setup

setup(
    name='elogy',
    author='Johan Forsberg',
    author_email='johan@slentrian.org',
    url='https://github.com/johanfforsberg/elogy',
    packages=['elogy'],
    include_package_data=True,
    install_requires=[
        'flask', 'peewee', 'blinker', 'lxml', 'pillow', 'dateutils'
    ],
)
