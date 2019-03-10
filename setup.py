from setuptools import setup
import os
import io
from towebm._version import __version__

# Read the long description from the README.
basedir = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(basedir, 'README.rst'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setup(
    name='towebm',
    version=__version__,
    description='A Python 3 script to convert videos to webm format (vp9+opus) using ffmpeg',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    author='David Gasaway',
    author_email='dave@gasaway.org',
    url='https://bitbucket.org/dgasaway/towebm',
    download_url='https://bitbucket.org/dgasaway/towebm/downloads/',
    license='GNU GPL v2',
    py_modules=['towebm/towebm', 'towebm/_version'],
    entry_points={
        'console_scripts': [
            'towebm = towebm.towebm:main',
        ],
    },
    python_requires='>=3.2',
    keywords='video converter ffmpeg vp9 opus webm',
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Topic :: Multimedia :: Video :: Conversion',
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
    ],
)
