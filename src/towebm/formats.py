# formats.py - Audio/video format definitions.
# Copyright (C) 2025 David Gasaway
# https://github.com/dgasaway/towebm

# This program is free software; you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not,
# see <http://www.gnu.org/licenses>.
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# --------------------------------------------------------------------------------------------------
@dataclass
class MappedCodecArg:
    """
    Represents an tool argument that maps directly to an ffmpeg codec arg.
    """
    short_flag: str | None
    """
    The short option string.
    """
    long_flag: str | None
    """
    The long option string.
    """
    ffmpeg_arg: str
    """
    The argument to pass to ffmpeg.
    """
    dest: str
    """
    The name of the attribute to be added to the namespace.
    """
    help: str = None
    """
    A brief description of what the argument does.
    """
    value_type: type = str
    """
    The type to which the command-line argument should be converted.
    """
    default: any = None
    """
    The default value for the argument.
    """
    metavar: str | None = None
    """
    A name for the argument in usage messages.
    """

# --------------------------------------------------------------------------------------------------
@dataclass
class AudioQualityArg(MappedCodecArg):
    """
    Represents an audio quality argument to add to a Converter CLI.
    """
    ffmpeg_value_suffix: str | None = None
    """
    The suffix to add to the quality value for the ffmpeg arg, if needed.
    """

# --------------------------------------------------------------------------------------------------
@dataclass
class Container:
    """
    Represents the attributes of a container format.
    """
    name: str
    """
    The name of the container format.
    """
    ffmpeg_format: str
    """
    The ffmpeg format name of the container format.
    """
    extension: str
    """
    The file extension to add for the container format.
    """
    supports_multiple_tracks: bool
    """
    True if the format supports multiple audio tracks, otherwise False.
    """

# --------------------------------------------------------------------------------------------------
class Containers:
    """
    Contains static `Container` instances of the defined container formats.
    """
    OGG: Final[Container] = Container("Ogg", "ogg", ".ogg", True)
    FLAC: Final[Container] = Container("FLAC", "flac", ".flac", False)
    MKV: Final[Container] = Container("Matroska", "matroska", ".mkv", True)
    WEBM: Final[Container] = Container("WebM", "webm", ".webm", True)
    MP4: Final[Container] = Container("MP4", "mp4", ".mp4", True)
    MP3: Final[Container] = Container("MP3", "mp3", ".mp3", True)

# --------------------------------------------------------------------------------------------------
@dataclass
class Format:
    """
    Represents the attributes of an audio or video format.
    """
    name: str
    """
    The name of the audio format.
    """
    ffmpeg_codec: str
    """
    The name of the corresponding ffmpeg codec.
    """
    containers: list[Container]
    """
    The list of supported container formats when the output is an audio file.
    """

# --------------------------------------------------------------------------------------------------
@dataclass
class AudioFormat(Format):
    """
    Represents the attributes of an audio format.
    """
    quality_arg: AudioQualityArg
    """
    The audio quality argument definition.
    """
    requires_channel_layout_fix: bool
    """
    True if the format requires mapping 5.1(side) to 5.1(rear) or similar for 5.0/4.1.
    """
    codec_args: list[str]
    """
    The ffmpeg codec arguments to add.  Arguments in index 0 are added for all passes, arguments in
    index 1 are added to pass 1, and so on.
    """

# --------------------------------------------------------------------------------------------------
class AudioFormats:
    """
    Contains static `AudioFormat` instances of the defined audio formts.
    """
    # vorbis output is not picky about channel layout.
    VORBIS: Final[AudioFormat] = AudioFormat(
        'Vorbis', 'libvorbis', [Containers.OGG],
        AudioQualityArg('-q', '--quality', '-q',
            dest='audio_quality',
            help='audio quality',
            value_type=float,
            default=6.0
        ),
        False,
        [ ]
    )
    # ffmpeg will create a multi-track opus file.  VLC will not play it; mplayer will.
    OPUS: Final[AudioFormat] = AudioFormat(
        'Opus', 'libopus', [Containers.OGG],
        AudioQualityArg('-b', '--bitrate', '-b',
            dest='audio_quality',
            help='audio bitrate in kbps',
            value_type=int,
            default=160,
            ffmpeg_value_suffix='k'
        ),
        True,
        [ ]
    )
    FLAC: Final[AudioFormat] = AudioFormat(
        'FLAC', 'flac', [Containers.FLAC, Containers.OGG],
        AudioQualityArg('-c', '--compression-level', '-compression-level',
            dest='audio_quality',
            help='audio compression level',
            value_type=int,
            default=8,
            metavar='COMP_LEVEL',
        ),
        False,
        [ ]
    )
    MP3: Final[AudioFormat] = AudioFormat(
        'MP3', 'libmp3lame', [Containers.MP3],
        AudioQualityArg('-q', '--quality', '-q',
            dest='audio_quality',
            help='audio quality in LAME VBR mode',
            value_type=float,
            default=4.0
        ),
        False,
        ['-compression_level', '0']
    )

# --------------------------------------------------------------------------------------------------
@dataclass
class VideoFormat(Format):
    """
    Represents the attributes of a video format.
    """
    passes: int
    """
    The number of encode passes for this format and codec.
    """
    audio_format: AudioFormat
    """
    The audio format to use for this video format.
    """
    mapped_codec_args: list[MappedCodecArg]
    """
    The list of mapped codec args.
    """
    codec_args: list[list[str]]
    """
    The ffmpeg codec arguments to add.  Arguments in index 0 are added for all passes, arguments in
    index 1 are added to pass 1, and so on.
    """

# --------------------------------------------------------------------------------------------------
class VideoFormats:
    """
    Contains static `VideoFormat` instances of the defined video formats.
    """
    WEBM: Final[VideoFormat] = VideoFormat(
        'VP9',
        'libvpx-vp9',
        [Containers.WEBM, Containers.MKV, Containers.MP4],
        2,
        AudioFormats.OPUS,
        [
            MappedCodecArg('-q', '--quality', '-crf',
                dest='video_quality',
                help='video quality, lower is better',
                value_type=int,
                default=30
            )
        ],
        [
            # All pass args.
            [
                '-b:v', '0',
                '-tile-columns', '2',
                '-row-mt', '1',
                '-auto-alt-ref', '1',
                '-lag-in-frames', '25',
                '-threads', '8',
                '-pix_fmt', 'yuv420p'
            ],
            # Pass one args.
            ['-cpu-used', '4'],
            # Pass two args.
            ['-cpu-used', '2']
        ]
    )

    AV1_SVT: Final[VideoFormat] = VideoFormat(
        'AV1',
        'libsvtav1',
        [Containers.MKV, Containers.MP4],
        1,
        AudioFormats.OPUS,
        [
            MappedCodecArg('-q', '--quality', '-crf',
                dest='video_quality',
                help='video quality, lower is better',
                value_type=int,
                default=30
            ),
            MappedCodecArg('-p', '--preset', '-preset',
                dest='preset',
                help='AV1-SVT preset; lower improves quality, higher improves speed',
                value_type=int,
                default=3
            )
        ],
        [ ]
    )

    AV1_AOM: Final[VideoFormat] = VideoFormat(
        'AV1',
        'libaom-av1',
        [Containers.MKV, Containers.MP4],
        2,
        AudioFormats.OPUS,
        [
            MappedCodecArg('-q', '--quality', '-crf',
                dest='video_quality',
                help='video quality, lower is better',
                value_type=int,
                default=30
            )
        ],
        [
            # All pass args.
            [
                '-b:v', '0',
                '-tile-columns', '2',
                '-row-mt', '1',
                '-auto-alt-ref', '1',
                '-lag-in-frames', '25'
            ],
            # Pass one args.
            ['-cpu-used', '4'],
            # Pass two args.
            ['-cpu-used', '2']
        ],
    )
