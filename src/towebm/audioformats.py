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
from enum import IntEnum
from typing import Final

# --------------------------------------------------------------------------------------------------
class AudioQualityType(IntEnum):
    """
    Represents the way that an audio codec expresses audio quality.
    """
    BITRATE = 1
    QUALITY = 2

# --------------------------------------------------------------------------------------------------
class AudioFormat:
    """
    Represents the attributes of an audio format.
    """
    def __init__(
        self,
        name: str,
        ffmpeg_codec: str,
        file_extension: str,
        quality_type: AudioQualityType,
        default_quality: float,
        supports_multi_tracks: bool,
        requires_channel_layout_fix: bool):
        
        self.name = name
        self.codec = ffmpeg_codec
        self.file_extension = file_extension
        self.quality_type = quality_type
        self.default_quality = default_quality
        self.supports_multi_tracks = supports_multi_tracks
        self.requires_channel_layout_fix = requires_channel_layout_fix
        
# --------------------------------------------------------------------------------------------------
# vorbis output is not picky about channel layout.
VORBIS: Final[AudioFormat] = AudioFormat(
    'vorbis', 'libvorbis', '.ogg', AudioQualityType.QUALITY, 6.0, True, False
)
# ffmpeg will create a multi-track opus file.  VLC will not play it; mplayer will.
OPUS: Final[AudioFormat] = AudioFormat(
    'opus', 'libopus', '.opus', AudioQualityType.BITRATE, 160, True, True
)
