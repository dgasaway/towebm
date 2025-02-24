# audioformats.py - Audio format definitions.
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
from enum import IntEnum
from typing import Final

# --------------------------------------------------------------------------------------------------
class AudioQualityType(IntEnum):
    """
    Represents the way that an audio codec expresses audio quality.
    """
    BITRATE = 1
    QUALITY = 2
    COMP_LEVEL = 3

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

# --------------------------------------------------------------------------------------------------
class Containers:
    """
    Contains static `Container` instances of the defined container formats.
    """
    OGG: Final[Container] = Container("Ogg", "ogg", ".ogg")
    FLAC: Final[Container] = Container("FLAC", "flac", ".flac")
    MKV: Final[Container] = Container("Matroska", "matroska", ".mkv")
    WEBM: Final[Container] = Container("WebM", "webm", ".webm")
    MP4: Final[Container] = Container("MP4", "mp4", ".mp4")

# --------------------------------------------------------------------------------------------------
@dataclass
class AudioFormat:
    """
    Represents the attributes of an audio format.
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
    quality_type: AudioQualityType
    """
    The audio quality type.
    """
    default_quality: float
    """
    The default audio quality.
    """
    supports_multi_tracks: bool
    """
    True if the format supports multiple audio tracks, otherwise False.
    """
    requires_channel_layout_fix: bool
    """
    True if the format requires mapping 5.1(side) to 5.1(rear) or similar for 5.0/4.1.
    """

# --------------------------------------------------------------------------------------------------
class AudioFormats:
    """
    Contains static `AudioFormat` instances of the defined audio formts.
    """
    # vorbis output is not picky about channel layout.
    VORBIS: Final[AudioFormat] = AudioFormat(
        'Vorbis', 'libvorbis', [Containers.OGG], AudioQualityType.QUALITY, 6.0,
        True, False
    )
    # ffmpeg will create a multi-track opus file.  VLC will not play it; mplayer will.
    OPUS: Final[AudioFormat] = AudioFormat(
        'Opus', 'libopus', [Containers.OGG], AudioQualityType.BITRATE, 160,
        True, True
    )
    FLAC: Final[AudioFormat] = AudioFormat(
        'FLAC', 'flac', [Containers.FLAC, Containers.OGG], AudioQualityType.COMP_LEVEL, 8,
        False, False
    )

# --------------------------------------------------------------------------------------------------
@dataclass
class VideoFormat:
    """
    Represents the attriburtes of a video format.
    """
    name: str
    """
    The name of the video format.
    """
    ffmpeg_codec: str
    """
    The name of the corresponding ffmpeg codec.
    """
    containers: list[Container]
    """
    The list of supported container formats.
    """
    passes: list[int]
    """
    A list of the passes for this format and codec.
    """
    audio_format: AudioFormat
    """
    The audio format to use for this video format.
    """
    default_quality: float
    """
    The default video quality.
    """
    video_quality_help: str
    """
    The help string used by the arg parser for the video quality argument.
    """
    video_quality_arg: str
    """
    The ffmpeg argument for the video quality argument.
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
        [1, 2],
        AudioFormats.OPUS,
        30,
        'video quality, lower is better',
        '-crf',
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
        ],
    )

    AV1_SVT: Final[VideoFormat] = VideoFormat(
        'AV1',
        'libsvtav1',
        [Containers.MKV, Containers.MP4],
        [1],
        AudioFormats.OPUS,
        30,
        'video quality, lower is better',
        '-crf',
        [
            # All pass args.
            ['-preset', '3']
        ]
    )

    AV1_AOM: Final[VideoFormat] = VideoFormat(
        'AV1',
        'libaom-av1',
        [Containers.MKV, Containers.MP4],
        [1, 2],
        AudioFormats.OPUS,
        30,
        'video quality, lower is better',
        '-crf',
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
