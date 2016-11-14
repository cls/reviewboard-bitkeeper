from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))

version = '0.1'

install_requires = [
    # List your project dependencies here.
    # For more details, see:
    # http://packages.python.org/distribute/setuptools.html#declaring-dependencies
    'ReviewBoard==2.5.7',
]

setup(name='reviewboard-bitkeeper',
    version=version,
    description="BitKeeper support for Review Board",

    classifiers=[
        # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 1 - Planning",
        "Framework :: Django :: 1.6",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Version Control"
    ],
    keywords='reviewboard bitkeeper',
    author='Connor Smith',
    author_email='connor.smith@hds.com',
    url='https://github.com/cls/reviewboard-bitkeeper',
    license='MIT License',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'reviewboard.scmtools': [
            'bk = reviewboard_bitkeeper.bk:BKTool',
        ]
    }
)
