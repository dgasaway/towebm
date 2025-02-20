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
class AudioFormat:
    """
    Represents the attributes of an audio format.
    """
    def __init__(
        self,
        codec_name: str,
        ffmpeg_codec: str,
        container: str,
        quality_type: AudioQualityType,
        default_quality: float,
        supports_multi_tracks: bool,
        requires_channel_layout_fix: bool):

        self.codec_name = codec_name
        self.ffmpeg_codec = ffmpeg_codec
        self.container = container
        self.quality_type = quality_type
        self.default_quality = default_quality
        self.supports_multi_tracks = supports_multi_tracks
        self.requires_channel_layout_fix = requires_channel_layout_fix

# --------------------------------------------------------------------------------------------------
class AudioFormats:
    # vorbis output is not picky about channel layout.
    VORBIS: Final[AudioFormat] = AudioFormat(
        'vorbis', 'libvorbis', 'ogg', AudioQualityType.QUALITY, 6.0, True, False
    )
    # ffmpeg will create a multi-track opus file.  VLC will not play it; mplayer will.
    OPUS: Final[AudioFormat] = AudioFormat(
        'opus', 'libopus', 'opus', AudioQualityType.BITRATE, 160, True, True
    )
    FLAC: Final[AudioFormat] = AudioFormat(
        'flac', 'flac', 'flac', AudioQualityType.COMP_LEVEL, 8, False, False
    )

# --------------------------------------------------------------------------------------------------
class VideoFormat:
    """
    Represents the attriburtes of a video format.
    """
    def __init__(
        self,
        codec_name: str,
        container_options: list[str],
        ffmpeg_codec: str,
        ffmpeg_output: str,
        passes: list[int],
        audio_format: AudioFormat,
        default_quality: float,
        video_quality_help: str,
        video_quality_arg: str,
        codec_args: list[str],
        pass1_codec_args: list[str],
        pass2_codec_args: list[str]):

        self.codec_name = codec_name
        self.ffmpeg_codec = ffmpeg_codec
        self.ffmpeg_output = ffmpeg_output
        self.passes = passes
        self.container_options = container_options
        self.audio_format = audio_format
        self.default_quality = default_quality
        self.video_quality_help = video_quality_help
        self.video_quality_arg = video_quality_arg
        self.codec_args = codec_args
        self.pass1_codec_args = pass1_codec_args
        self.pass2_codec_args = pass2_codec_args

# --------------------------------------------------------------------------------------------------
class VideoFormats:
    WEBM: Final[VideoFormat] = VideoFormat(
        'VP9', ['webm', 'mkv'], 'libvpx-vp9', 'webm', [1, 2], AudioFormats.OPUS, 30,
        'video quality, lower is better',
        '-crf',
        codec_args=[
            '-b:v', '0',
            '-tile-columns', '2',
            '-row-mt', '1',
            '-auto-alt-ref', '1',
            '-lag-in-frames', '25',
            '-threads', '8',
            '-pix_fmt', 'yuv420p'
        ],
        pass1_codec_args=[ '-cpu-used', '4' ],
        pass2_codec_args=[ '-cpu-used', '2' ]
    )
