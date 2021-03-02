#!/usr/bin/python3

# towebm - Converts audio/video files to audio-only opus using ffmpeg.
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
from towebm.common import *

# --------------------------------------------------------------------------------------------------
def main():
    parser = ArgumentParser(
        description='Converts audio/video files to audio-only opus using ffmpeg.',
        fromfile_prefix_chars="@")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('-b', '--bitrate',
        help='audio bitrate in kbps (default 160)',
        action='store', type=int, default=160)

    parser.add_argument('-#', '--always-number',
        help='always add a number to the output file name',
        action='store_true', default=False)
    parser.add_argument('--pretend',
        help='display command lines but do not execute',
        action='store_true')
    parser.add_argument('-v', '--verbose',
        help='verbose output',
        action='store_true')

    # Timecode/segment arguments.    
    sgroup = parser.add_argument_group('source segment arguments',
        'A single segment or multiple segments of a source file may be encoded using the '
        'following arguments.  The first three may be used independently or combined, while the '
        'last not not be combined with the first three.  The same arguments will be applied to '
        'all source files.  All argument values are in ffmpeg duration format; see ffmpeg '
        'documentation for more details.')
    sgroup.add_argument('--start',
        help='starting source position',
        action='store')
    sgroup.add_argument('--duration',
        help='duration to encode',
        action='store')
    sgroup.add_argument('--end',
        help='ending source position',
        action='store')
    sgroup.add_argument('--segment',
        help='segment start and end source position; my be specified multiple times to encode '
             'multiple segments to separate files; enables --always-number when specified more '
             'than once',
        nargs=2, metavar=('START', 'END'), action='append', dest='segments')

    # Video/audio filter arguments.
    fgroup = parser.add_argument_group('filter arguments')
    fgroup.add_argument('--fade-in',
        help='apply an audio and video fade-in at the start of each output',
        action='store', type=float, metavar='SECONDS')
    fgroup.add_argument('--fade-out',
        help='apply an audio and video fade-out at the end of each output',
        action='store', type=float, metavar='SECONDS')
    fgroup.add_argument('-f', '--filter',
        help='custom audio filter, passed as -af argument to ffmpeg',
        action='append', dest='audio_filter')
    fgroup.add_argument('--volume', 
        help='amplitude (volume) multiplier, < 1.0 to reduce volume, or > 1.0 to increase volume; '
             'recommended to use replaygain to tag the file post-conversion, instead',
        action='store', type=float, default=1.0)

    parser.add_argument('source_files',
        help='source video files to convert',
        action='store', metavar='source_file', nargs='+')
    args = parser.parse_args()

    if args.segments is not None and len(args.segments) > 1:
        args.always_number = True

    if args.verbose >= 1:
        print (args)

    # Check for invalid combinations.
    if args.duration is not None and args.end is not None:
        parser.error('--duration and --end may not be used together')
    if args.start is not None or args.duration is not None or args.end is not None:
        if args.segments is not None:
            parser.error('--segments may not be used with other segment selectors')
    if args.fade_out is not None:
        if args.duration is None and args.end is None and args.segments is None:
            parser.error('--fade-out requires --duration, --end, or --segment')

    # Check for valid files.
    for source_file in args.source_files:
        if not os.path.exists(source_file):
            parser.error('invalid source file: ' + source_file)

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
    title = os.path.splitext(os.path.basename(file_name))[0]
    
    result = ['ffmpeg', '-nostdin', '-hide_banner']
    result += get_segment_arguments(segment)
    result += [
        '-i', file_name,
        '-vn',
        '-c:a', 'libopus',
        '-b:a', '{0}k'.format(args.bitrate)
        ]
    result += get_audio_filters(args, segment)
    result += [
        #'-metadata:s:a:0', 'title={0}'.format(title),
        get_safe_filename(title + '.opus', args.always_number)
        ]

    return result

# --------------------------------------------------------------------------------------------------
def process_segment(args, segment, file_name):
    cmd = get_ffmpeg_command(args, segment, file_name)
    if args.pretend or args.verbose >= 1:
        print(cmd)
    if not args.pretend:
        subprocess.check_call(cmd)
    
# --------------------------------------------------------------------------------------------------
def process_file(args, file_name):
    if args.segments is not None:
        for segment in args.segments:
            process_segment(args, Segment(segment[0], segment[1], None), file_name)
    else:
        process_segment(args, Segment(args.start, args.end, args.duration), file_name)

# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
