# tovorbis.py - Converts audio/video files to audio-only vorbis using ffmpeg.
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
import sys

from towebm.converters import AudioConverter
from towebm.formats import AudioFormats

# --------------------------------------------------------------------------------------------------
def main() -> int:
    return AudioConverter(AudioFormats.VORBIS).main()

# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
