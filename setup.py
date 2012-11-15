from distutils.core import setup

setup(
    name='pynacha',
    version='0.0.1',
    description=("A library to generate NACHA files - see https://www.nacha.org/"),
    long_description=("A library to generate NACHA files - see https://www.nacha.org/"),
    author='Matt Pegler',
    author_email='matt@pegler.co',
    url='http://github.com/pegler/pynacha',
    packages=[
        'pynacha',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)