from setuptools import setup, find_packages
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
    description=
        'Python 3 scripts which use ffmpeg to convert videos to webm format (vp9+opus) or to '
        'convert audio to opus or vorbis.',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    author='David Gasaway',
    author_email='dave@gasaway.org',
    url='https://github.com/dgasaway/towebm',
    download_url='https://github.com/dgasaway/towebm/releases',
    license='GNU GPL v2',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'towebm = towebm.towebm:main',
            'toopus = towebm.toopus:main',
            'tovorbis = towebm.tovorbis:main',
            'ffcat = towebm.ffcat:main',
        ],
    },
    python_requires='>=3.2',
    keywords='video converter ffmpeg vp9 opus webm vorbis',
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Multimedia :: Sound/Audio :: Conversion',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
    ],
)
