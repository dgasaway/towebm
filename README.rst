Introduction
============

``towebm`` is a Python 3 script to transcode video files to a webm container
with VP9 format video and Opus format audio using the ``ffmpeg`` tool.
Arguments are available for basic edit operations - crop, scale, cut, 
grayscale, and deinterlate - as well as for passing arbitrary ffmpeg video
or audio filters.


Usage
=====

Transcode a source MP2 video with no edits and default quality settings::

    towebm Great*.mpg

Transcode a source 1920x1080 MP4 video, which is cropped to 4:3 ratio
(1440x1080), then scaled to 720 vertical resolution (960x720), and converted
to grayscale.  Video quality is set to 25::

    towebm -q 25 -s crop43 -s scale23 -s gray Three*.mp4

Transcode a source MP4 video with a 140 and 144 crop from the top and bottom,
respectively::
    
    towebm -y 140 144 Music*.mp4

Transcode a source MKV video with a crop to all sides and an aspect-correct
scale to 706 horizontal resolution::
    
    towebm -x 260 260 -y 16 4 -f "scale=h=706:w=-1" Calif*.mkv

Installation
============

.. warning::

    Some Linux distributions discourage installation of system-level python
    packages using ``pip`` or ``setup.py install``, due to collisions with the
    system package manager.  In those cases, dependencies should be installed
    through the package manager, if possible, or choose a user folder
    installation method.

Installing with pip
-------------------

If your system has ``pip`` installed, and you have access to install software in
the system packages, then *kantag* kan be installed as administrator from 
`PyPI <https://pypi.python.org/pypi>`_::

    # pip install towebm

If you do not have access to install system packages, or do not wish to install
in the system location, it can be installed in a user folder::

    $ pip install --user towebm

Installing from source
----------------------

Either download a release tarball from the
`Downloads <https://bitbucket.org/dgasaway/towebm/downloads/>`_ page, and
unpack::

    $ tar zxvf towebm-1.0.0.tar.gz

Or get the latest source from the Mercurial repository::

    $ hg clone https://bitbucket.org/dgasaway/towebm

If you have access to install software in the system packages, then it can be
installed as administrator::

    # python setup.py install

If you do not have access to install system packages, or do not wish to install
in the system location, it can be installed in a user folder::

    $ python setup.py install --user
