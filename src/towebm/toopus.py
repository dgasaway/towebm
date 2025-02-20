#!/usr/bin/env python3

# towebm - Converts audio/video files to audio-only opus using ffmpeg.
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

import os
import subprocess
import sys
from argparse import ArgumentParser
from towebm.argparsers import ToolArgumentParser, DelimitedValueAction
from towebm.common import *


# --------------------------------------------------------------------------------------------------
def main():
    """
    Executes the operations indicated by the command line arguments.
    """
    args = parse_args()

    # We'll treat each input file as it's own job, and continue to the next if there is a problem.
    rc = 0
    for source_file in args.source_files:
        try:
            process_file(args, source_file)
        except subprocess.CalledProcessError as e:
            if rc == 0 or e.returncode > rc:
                rc = e.returncode
            print('Execution error, proceeding to next source file.')

    return rc

# --------------------------------------------------------------------------------------------------
def parse_args():
    """
    Parses and returns the command line arguments.
    """
    parser = ToolArgumentParser(
        description='Converts audio/video files to audio-only opus using ffmpeg.',
        fromfile_prefix_chars='@')
    parser.add_basic_arguments()
    parser.add_argument('-b', '--bitrate',
        help='audio bitrate in kbps (default 160); may be a colon-delimited list to select from '
             'multiple source audio tracks, with value 0 or blank used to skip a track',
        action=DelimitedValueAction, dest='audio_quality', metavar='BITRATE', value_type=int,
        default=[160])
    parser.add_argument('--channel-layout-fix',
        help='apply a channel layout fix to 4.1, 5.0, 5.1(side) audio sources to output a '
             'compatible 5.1(rear) layout; may be a colon-delimited list to apply the fix to '
             'multiple audio tracks from the source; use 0 or blank to apply no fix',
        action=DelimitedValueAction, metavar="FIX_STRING",
        value_choices=['0', '4.1', '5.0', '5.1'], default=['0'])
    parser.add_timecode_arguments()
    parser.add_audio_filter_arguments()
    parser.add_source_file_arguments()
    parser.add_passthrough_arguments()

    # Parse the arguments and do extra argument checks.
    args = parser.parse_args()
    qcnt = len([q for q in args.audio_quality if q is not None and q > 0])
    if qcnt < 1:
        parser.error('at least one positive audio bitrate must be specified')
    elif qcnt > 1:
        parser.error('only one non-zero audio bitrate may be specified')

    if args.verbose >= 1:
        print (args)

    return args

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
        '-c:a', 'libopus'
        ]
    result += get_audio_filter_args(args, segment)
    result += get_audio_quality_args(args)
    result += get_audio_metadata_map_args(args)
    result += args.passthrough_args
    result += [get_safe_filename(title + '.opus', args.always_number)]

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
    sys.exit(main())
