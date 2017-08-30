from setuptools import setup

setup(
    name='elogy',
    author='Johan Forsberg',
    author_email='johan@slentrian.org',
    url='https://github.com/johanfforsberg/elogy',
    packages=['elogy'],
    include_package_data=True,
    install_requires=[
        'flask',
        'webargs',
        'peewee',
        'blinker',
        'lxml',
        'pillow',
        'dateutils',
        'flask-restful',
        'pyldap',  # should be optional, depends on libpdap and libsasl!
        'flask-admin',  # maybe also optional?
        'wtf-peewee'
    ],
)
