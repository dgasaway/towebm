#!/usr/bin/python3

# ffcat - Concatenates media files using ffmpeg.
# Copyright (C) 2021 David Gasaway
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
import os
import subprocess
from argparse import ArgumentParser
from towebm._version import __version__
from tempfile import NamedTemporaryFile

# --------------------------------------------------------------------------------------------------
def main():
    parser = ArgumentParser(
        description='Concatenates media files using the ffmpeg concat demuxer.',
        fromfile_prefix_chars="@")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('-v', '--verbose',
        help='verbose output',
        action='store_true')
    parser.add_argument('source_files',
        help='sources files to concatenate',
        action='store', metavar='source_file', nargs='+')
    parser.add_argument('output_file',
        help='output file name', action='store')
    args = parser.parse_args()

    if args.verbose >= 1:
        print(args)

    file_list = NamedTemporaryFile(mode='wt', dir=os.getcwd(), delete=False)
    try:
        for source_file in args.source_files:
            file_list.write("file '{0}'\n".format(source_file.replace("'", r"'\''")))
        file_list.close()
        ffmpeg_args = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', file_list.name, '-c', 'copy',
                       args.output_file]
        if args.verbose >= 1:
            print(ffmpeg_args)
        subprocess.check_call(ffmpeg_args)
    finally:
        os.remove(file_list.name)
