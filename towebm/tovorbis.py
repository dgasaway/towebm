#!/usr/bin/python3

# towebm - Converts audio/video files to audio-only vorbis using ffmpeg.
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
from towebm.common import *

# --------------------------------------------------------------------------------------------------
def main():
    """
    Parses command line argument and initiates main operation.
    """
    parser = ArgumentParser(
        description='Converts audio/video files to audio-only vorbis using ffmpeg.',
        fromfile_prefix_chars="@")
    add_basic_arguments(parser)
    parser.add_argument('-q', '--quality',
        help='audio quality (default 6.0); may be specified multiple times to include additional '
             'audio tracks from the source, with value 0 used to skip a track',
        action='append', dest='audio_quality', metavar='QUALITY', type=float)

    # Timecode/segment arguments.
    add_timecode_arguments(parser)

    # Filter arguments.
    add_audio_filter_arguments(parser)

    parser.add_argument('source_files',
        help='source video files to convert',
        action='store', metavar='source_file', nargs='+')
    args = parser.parse_args()

    if args.segments is not None and len(args.segments) > 1:
        args.always_number = True

    if args.verbose >= 1:
        print (args)
    if args.audio_quality is None:
        args.audio_quality = 6.0
    elif len([q for q in args.audio_quality if q > 0]) < 1:
        parser.error('at least one positive audio quality must be specified')

    check_timecode_arguments(parser, args)
    check_source_files_exist(parser, args)

    ret = 0
    for source_file in args.source_files:
        try:
            process_file(args, source_file)
        except subprocess.CalledProcessError as e:
            if ret == 0 or e.returncode > ret:
                ret = e.returncode
            print('Execution error, proceeding to next source file.')
    exit(ret)

# --------------------------------------------------------------------------------------------------
def get_ffmpeg_command(args, segment, file_name):
    """
    Returns the arguments to run ffmpeg for a single output file.
    """
    title = os.path.splitext(os.path.basename(file_name))[0]
    
    result = ['ffmpeg', '-nostdin', '-hide_banner']
    result += get_segment_arguments(segment)
    result += [
        '-i', file_name,
        '-vn',
        '-c:a', 'libvorbis'
        ]
    result += get_audio_filter_args(args, segment)
    result += get_audio_quality_args(args)
    result += get_audio_metadata_map_args(args)
    result += [get_safe_filename(title + '.ogg', args.always_number)]

    return result

# --------------------------------------------------------------------------------------------------
def process_segment(args, segment, file_name):
    """
    Executes the requested action for a single output file.
    """
    cmd = get_ffmpeg_command(args, segment, file_name)
    if args.pretend or args.verbose >= 1:
        print(cmd)
    if not args.pretend:
        subprocess.check_call(cmd)
    
# --------------------------------------------------------------------------------------------------
def process_file(args, file_name):
    """
    Executes the requested action for a single input file.
    """
    if args.segments is not None:
        for segment in args.segments:
            process_segment(args, Segment(segment[0], segment[1], None), file_name)
    else:
        process_segment(args, Segment(args.start, args.end, args.duration), file_name)

# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
