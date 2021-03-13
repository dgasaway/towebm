Introduction
============

``towebm`` is a Python 3 script to transcode video files to a webm container
with VP9 format video and Opus format audio using the ``ffmpeg`` tool.
Arguments are available for basic edit operations - crop, scale, cut, 
grayscale, and deinterlate - as well as for passing arbitrary ffmpeg video
or audio filters.  ``toopus`` and ``tovorbis`` will transcode audio from
video or audio files to Opus and Vorbis format files, respectively, with
many of the same features as ``towebm``.  Finally, ``ffcat`` will
concatenate files using the ``concat`` demuxer, intended for joining multiple
output segments produced by ``towebm`` from a single input file.

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

Transcode two minutes of a video, starting ten seconds from the start, using
three different available options::

    towebm --start 10 --duration 2:00 Calif*.mkv
    towebm --start 0:10 --duration 2:10 Calif*.mkv
    towebm --segment 0:10 2:10 Calif*.mkv

Transcode multiple segments of a video, with one output per segment::

    towebm input.mp4 \
        --segment 00:00:30.300 00:07:04.900 \
        --segment 00:09:44.366 00:14:30.133 \
        --segment 20:42:49.300 29:20:01.400

Same as the previous example, but using multiple executions (especially useful
if different filters need to be applied to the different segments)::

    towebm input.mp4 -# --segment 00:00:30.300 00:07:04.900
    towebm input.mp4 -# --segment 00:09:44.366 00:14:30.133
    towebm input.mp4 -# --segment 20:42:49.300 29:20:01.400

Join the output of the previous example into a single file::

    ffcat input_*.webm final.webm
    
Transcode a segment of a video with a one second fade-in and half-second
fade-out::

    towebm input.mp4 --start 1:00 --end 2:00 --fade-in 1 --fade-out 0.5
    
Same as the previous example, but producing an output file with only opus
audio::

    towebm input.mp4 --start 1:00 --end 2:00 --fade-in 1 --fade-out 0.5

Transcode a portion of a FLAC audio file to vorbis, quality 4::

    tovorbis -q 4 --start 1:00 --end 2:00 input.flac
    
Installation
============

Warning
-------

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
`Downloads <https://github.com/dgasaway/towebm/releases>`_ page, and
unpack::

    $ tar zxvf towebm-1.0.0.tar.gz

Or get the latest source from the git repository::

    $ git clone https://github.com/dgasaway/towebm.git

If you have access to install software in the system packages, then it can be
installed as administrator::

    # python setup.py install

If you do not have access to install system packages, or do not wish to install
in the system location, it can be installed in a user folder::

    $ python setup.py install --user
