Introduction
============

The *towebm* package includes a set of Python 3 scripts for transcoding audio or video files using
FFmpeg_.  Arguments are available for basic edit operations -- crop, scale, cut, deinterlace -- and
more.  Arbitrary ffmpeg video and audio filters can also be specified.   Most outputs also support
multiple audio tracks, e.g., surround sound and stereo.  The included scripts are as follows:

``towebm``
    Transcodes video files to VP9_ video and Opus_ audio in a WebM_ container.

``toopus``
    Transcodes audio or video files to Opus_ audio in an Ogg_ container.

``tovorbis``
    Transcodes audio or video files to Vorbis_ audio in an Ogg_ container.

``toflac``
    Transcodes audio or video files to FLAC_ audio in the native container.

``ffcat``
    Concatenates multiple files of the same resolution and codec to a single file.  Most usefeul
    when ``towebm`` has produced multiple output files as edits of a single source file.

Usage
=====

Transcode a source MP2 video with no edits and default quality settings::

    towebm Great*.mpg

Transcode a source 1920x1080 MP4 video, which is cropped to 4:3 ratio (1440x1080), then scaled to
720 vertical resolution (960x720), and converted to grayscale.  Video quality is set to 25::

    towebm -q 25 -s crop43 -s scale23 -s gray Three*.mp4

Transcode a source MP4 video with a 140 and 144 crop from the top and bottom, respectively::
    
    towebm -y 140 144 Music*.mp4

Transcode a source MKV video with a crop to all sides and an aspect-correct scale to 706 horizontal
resolution::
    
    towebm -x 260 260 -y 16 4 -vf "scale=h=706:w=-1" Calif*.mkv

Transcode two minutes of a video, starting ten seconds from the start, using three different
available options::

    towebm --start 10 --duration 2:00 Calif*.mkv
    towebm --start 0:10 --duration 2:10 Calif*.mkv
    towebm --segment 0:10 2:10 Calif*.mkv

Transcode multiple segments of a video, with one output per segment::

    towebm input.mp4 \
        --segment 00:00:30.300 00:07:04.900 \
        --segment 00:09:44.366 00:14:30.133 \
        --segment 20:42:49.300 29:20:01.400

Same as the previous example, but using multiple executions (especially useful if different filters
need to be applied to the different segments)::

    towebm input.mp4 -# --segment 00:00:30.300 00:07:04.900 --fade-in 0.5
    towebm input.mp4 -# --segment 00:09:44.366 00:14:30.133
    towebm input.mp4 -# --segment 20:42:49.300 29:20:01.400 --fade-out 0.5

Join the output of the previous example into a single file::

    ffcat input_*.webm final.webm

Transcode a source MKV video with three audio tracks, the first of which is a 5.1(side)
surround-sound track::

    towebm input.mkv --fix-channel-layout 5.1:0:0 -b 256:128:128

Same as the previous example, but excluding the first audio track from the output::

    towebm input.mkv b 0:128:128

Transcode a segment of a video to Opus audio, with a one second fade-in and a half-second fade-out::

    toopus input.mp4 --start 1:00 --end 2:00 --fade-in 1 --fade-out 0.5

Transcode a portion of a FLAC audio file to vorbis, quality 4::

    tovorbis -q 4 --start 1:00 --end 2:00 input.flac

Transcode the second audio track of a source video file to FLAC, compression level 6::

    toflac input.avi -c 0:6

Transcode a video file, scaled to 960x720 and aspect ratio forced to 4:3.  Useful if the input
video has an incorrect aspect ratio.  See the `FFmpeg filters`_  documentation for more
information::

    towebm input.mkv -vf "scale=w=960:h=720,setdar=4/3"


Installation
============

FFmpeg
------

FFmpeg must be installed separately from *towebm* and located in the system search path for the
scripts to work properly.  For operating systems with system-level package management, look for
FFmpeg in the repository.  On Windows, one can try Chocolatey_, WinGet_, or Cygwin_.

Warning
-------

    Linux and BSD distributions typically manage system-level Python packages through their own
    repository and distribution system -- apt, zypper, yum, ports, portage, etc.  While the scripts
    included here have no dependencies beyond the standard libraries and this time, and are thus
    unlikely to cause system conflicts, it is still advisable to install them as a user package or
    in a Python virtual environment.  *pipx*, if available for your system, is the recommended
    installation method.  On Windows, *pip* is easily available with Python and generally safe.

Installing with pipx
--------------------

Instructions for installing *pipx* on popular operating systems are available on the pipx_ website,
otherwise consult your operating system documentation.  By default, *pipx* will install the scripts
into a virtual environment.  You may need to add a path to your search path to run the scripts
without specifying a path.  Use the following to install the package from PyPI_::

    $ pipx install towebm

Installing with pip
-------------------

By default, *pip* will install *towebm* as a system package, which may require administrative
priveleges.  Use the following to install the package from PyPI_::

    # pip install towebm

If you do not have access to install system packages, or do not wish to install
in the system location, it can be installed in a user folder::

    $ pip install --user towebm

Installing from source
----------------------

Either download a release tarball from the Downloads_ page, and unpack::

    $ tar zxvf towebm-1.1.0.tar.gz

Or get the latest source from the git repository::

    $ git clone https://github.com/dgasaway/towebm.git

Use one of the following in the project directory, after reading about *pip* and *pipx* above::

    $ pipx install .
    $ pip install --user .
    $ pip install .

A script can be run directly from source without installation, though this is not convenient.  For
example, while in the *src* directory::

    $ PYTHONPATH=towebm python -m tovorbis

.. _FFmpeg: https://ffmpeg.org/
.. _VP9: https://developers.google.com/media/vp9/
.. _Opus: https://opus-codec.org/
.. _Ogg: https://www.xiph.org/ogg/
.. _WebM: https://www.webmproject.org/
.. _Vorbis: https://www.xiph.org/vorbis/
.. _FLAC: https://xiph.org/flac/
.. _FFmpeg filters: https://ffmpeg.org/ffmpeg-filters.html
.. _Chocolatey: https://chocolatey.org/
.. _WinGet: https://learn.microsoft.com/en-us/windows/package-manager/
.. _Cygwin: https://cygwin.com
.. _pipx: https://pipx.pypa.io/latest/installation/
.. _PyPI: https://pypi.python.org/pypi
.. _Downloads: https://github.com/dgasaway/towebm/releases
