#!/usr/bin/python3

# towebm - Converts videos to webm format (vp9+opus) using ffmpeg.
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
from datetime import datetime
from argparse import ArgumentParser
from collections.abc import Sequence
from towebm.common import *

# --------------------------------------------------------------------------------------------------
def main():
    """
    Parses command line argument and initiates main operation.
    """
    parser = ArgumentParser(
        description='Converts videos to webm format (vp9+opus) using a two-pass ffmpeg encode.',
        fromfile_prefix_chars="@")
    add_basic_arguments(parser)
    parser.add_argument('-q', '--quality',
        help='video quality (lower is better, default 30)',
        action='store', type=int, default=30)
    parser.add_argument('-b', '--audio-bitrate',
        help='audio bitrate in kbps (default 160); may be specified multiple times to include '
             'additional audio tracks from the source, with value 0 used to skip a track',
        action='append', dest='audio_quality', metavar='AUDIO_BITRATE', type=int)
    # Note: 'pass' is a keyword, so used name 'only_pass' internally.
    parser.add_argument('--pass',
        help='run only a given pass',
        action='store', choices=['1', '2'], dest='only_pass')
    parser.add_argument('--delete-log',
        help='delete pass 1 log (otherwise keep with timestamp)',
        action='store_true')
    parser.add_argument('-C', '--container',
        help='container format (default webm)',
        action='store', choices=['webm', 'mkv'], default='webm')

    # Timecode/segment arguments.    
    add_timecode_arguments(parser)

    # Video/audio filter arguments.
    fgroup = parser.add_argument_group('video/audio filter arguments',
        'The deinterlate filter is applied first; standard crop filters (e.g., "-s crop43") are '
        'applied before custom crop values (e.g., "-x 10 10"); crop filters are applied before '
        'scale filters (e.g., "-s scale23");  and all standard filters are applied before custom '
        '(i.e., "-f" and "-a") filters.')
    fgroup.add_argument('-s', '--standard-filter',
        help='standard video/audio filter; '
             '[crop43] crops horizontally to 4:3 aspect ratio; '
             '[scale23] scales down by 2/3 (e.g., 1080p to 720p); '
             '[gray] converts to grayscale',
        action='append', choices=['crop43', 'scale23', 'gray'])
    fgroup.add_argument('-d', '--deinterlace',
        help='deinterlate filter (bwdif); '
             '[frame] output a frame from each pair of input fields; '
             '[field] output an interpolated frame from each input field',
        action='store', choices=['frame', 'field'])
    fgroup.add_argument('--parity',
        help='set a specific parity for the deinterlace filter; '
             '[tff] top field first; '
             '[bff] bottom field first',
        action='store', choices=['tff', 'bff'])
    fgroup.add_argument('--fade-in',
        help='apply an audio and video fade-in at the start of each output',
        action='store', type=float, metavar='SECONDS')
    fgroup.add_argument('--fade-out',
        help='apply an audio and video fade-out at the end of each output',
        action='store', type=float, metavar='SECONDS')
    fgroup.add_argument('-x', '--crop-width',
        help='left and right crop values',
        nargs=2, type=int, metavar=('LEFT', 'RIGHT'))
    fgroup.add_argument('-y', '--crop-height',
        help='top and bottom crop values',
        nargs=2, type=int, metavar=('TOP', 'BOTTOM'))
    fgroup.add_argument('-g', '--gamma',
        help='gramma correction (default 1.0; no correction)',
        action='store', type=float, default=1.0)
    fgroup.add_argument('-f', '--filter',
        help='custom video filter, similar to -vf ffmpeg argument',
        action='append')
    fgroup.add_argument('-a', '--audio-filter',
        help='custom audio filter, similar to -af ffmpeg argument',
        action='append')
    fgroup.add_argument('--volume', 
        help='amplitude (volume) multiplier, < 1.0 to reduce volume, or > 1.0 to increase volume',
        action='store', type=float, default=1.0)

    parser.add_argument('source_files',
        help='source video files to convert',
        action='store', metavar='source_file', nargs='+')
    args = parser.parse_args()

    if args.segments is not None and len(args.segments) > 1:
        args.always_number = True
    if args.audio_quality is None:
        args.audio_quality = 160
    elif len([q for q in args.audio_quality if q > 0]) < 1:
        parser.error('at least one positive audio bitrate must be specified')

    if args.verbose >= 1:
        print (args)

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
def get_pass1_command(args, segment, file_name):
    """
    Returns the arguments to run ffmpeg for pass one of a single output file.
    """
    title = os.path.splitext(os.path.basename(file_name))[0]

    result = ['ffmpeg', '-nostdin', '-hide_banner']
    result += get_segment_arguments(segment)
    result += [
        '-i', file_name,
        '-c:v', 'libvpx-vp9',
        '-crf', str(args.quality),
        '-b:v', '0',
        '-tile-columns', '2',
        '-row-mt', '1',
        '-auto-alt-ref', '1',
        '-lag-in-frames', '25',
        '-pix_fmt', 'yuv420p'
        ]
    result += get_video_filter_args(args, segment)
    result += [
        '-an',
        '-f', 'webm',
        '-threads', '8',
        '-pass', '1',
        '-passlogfile', title,
        '-cpu-used', '4',
        '-y',
        '/dev/null'
        ]

    return result


# --------------------------------------------------------------------------------------------------
def get_pass2_command(args, segment, file_name):
    """
    Returns the arguments to run ffmpeg for pass two of a single output file.
    """
    title = os.path.splitext(os.path.basename(file_name))[0]
    
    result = ['ffmpeg', '-nostdin', '-hide_banner']
    result += get_segment_arguments(segment)
    result += [
        '-i', file_name,
        '-c:v', 'libvpx-vp9',
        '-crf', str(args.quality),
        '-b:v', '0',
        '-tile-columns', '2',
        '-row-mt', '1',
        '-auto-alt-ref', '1',
        '-lag-in-frames', '25',
        '-pix_fmt', 'yuv420p'
        ]
    result += get_video_filter_args(args, segment)
    result += ['-c:a', 'libopus']
    result += get_audio_filter_args(args, segment)
    result += get_audio_quality_args(args)
    result += [
        '-f', 'webm',
        '-threads', '8',
        '-pass', '2',
        '-passlogfile', title,
        '-cpu-used', '2',
        '-metadata', 'title={0}'.format(title)
        ]
    result += get_audio_metadata_map_args(args)
    result += [get_safe_filename(title + '.' + args.container, args.always_number)]

    return result

# --------------------------------------------------------------------------------------------------
def get_log_command(args, file_name):
    """
    Returns the arguments to either delete or rename the pass one log file, as requested by the
    user in the script arguemnts.
    """
    title = os.path.splitext(os.path.basename(file_name))[0]
    if args.delete_log:
        return ['rm', '{0}-0.log'.format(title)]
    else:
        return ['mv', 
                '{0}-0.log'.format(title),
                '{0}_{1:%Y%m%d-%H%M%S}.log'.format(title, datetime.now())]

# --------------------------------------------------------------------------------------------------
def process_segment(args, segment, file_name):
    """
    Executes the requested action for a single output file.
    """
    if args.only_pass is None or args.only_pass == '1':
        pass1cmd = get_pass1_command(args, segment, file_name)
        if args.pretend or args.verbose >= 1:
            print(pass1cmd)
        if not args.pretend:
            subprocess.check_call(pass1cmd)
    if args.only_pass is None or args.only_pass == '2':
        pass2cmd = get_pass2_command(args, segment, file_name)
        logcmd = get_log_command(args, file_name)
        if args.pretend or args.verbose >= 1:
            print(pass2cmd)
        if not args.pretend:
            subprocess.check_call(pass2cmd)
        if args.pretend or args.verbose >= 1:
            print(logcmd)
        if not args.pretend:
            subprocess.check_call(logcmd)
    
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
