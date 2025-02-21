# toav1 - Converts videos to av1 format (av1+opus) using ffmpeg.
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

from towebm.converters import VideoConverter
from towebm.formats import VideoFormats

# --------------------------------------------------------------------------------------------------
def main() -> int:
    return VideoConverter(VideoFormats.AV1).main()

# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
