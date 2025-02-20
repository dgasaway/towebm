# towebm - Converts videos to webm format (vp9+opus) using ffmpeg.
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

import os
import subprocess
import sys
from datetime import datetime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from argparse import Namespace

from towebm import common
from towebm.argparsers import VideoConverterArgumentParser
from towebm.formats import VideoFormats

# --------------------------------------------------------------------------------------------------
def main() -> int:
    """
    Executes the operations indicated by the command line arguments.
    """
    args = VideoConverterArgumentParser(VideoFormats.WEBM).parse_args()
    if args.verbose >= 1:
        print (args)

    # We'll treat each input file as it's own job, and continue to the next if there is a problem.
    rc = 0
    for source_file in args.source_files:
        try:
            process_file(args, source_file)
        except subprocess.CalledProcessError as ex:
            if rc == 0 or ex.returncode > rc:
                rc = ex.returncode
            print('Execution error, proceeding to next source file.')

    return rc

# --------------------------------------------------------------------------------------------------
def get_pass1_command(args: Namespace, segment: common.Segment, file_name: str) -> list[str]:
    """
    Returns the arguments to run ffmpeg for pass one of a single output file.
    """
    title = os.path.splitext(os.path.basename(file_name))[0]

    result = ['ffmpeg', '-nostdin', '-hide_banner']
    result += common.get_segment_arguments(segment)
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
    result += common.get_video_filter_args(args, segment)
    result += [
        '-an',
        '-f', 'webm',
        '-threads', '8',
        '-pass', '1',
        '-passlogfile', title,
        '-cpu-used', '4',
        '-y'
        ]
    result += args.passthrough_args
    result += ['/dev/null']

    return result

# --------------------------------------------------------------------------------------------------
def get_pass2_command(args: Namespace, segment: common.Segment, file_name: str) -> list[str]:
    """
    Returns the arguments to run ffmpeg for pass two of a single output file.
    """
    title = os.path.splitext(os.path.basename(file_name))[0]

    result = ['ffmpeg', '-nostdin', '-hide_banner']
    result += common.get_segment_arguments(segment)
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
    result += common.get_video_filter_args(args, segment)
    if len([q for q in args.audio_quality if q is not None and q > 0]) > 0:
        result += ['-c:a', 'libopus']
    else:
        result += ['-an']
    result += common.get_audio_filter_args(args, segment)
    result += common.get_audio_quality_args(args)
    result += [
        '-f', 'webm',
        '-threads', '8',
        '-pass', '2',
        '-passlogfile', title,
        '-cpu-used', '2',
        '-metadata', f'title={title}'
        ]
    result += common.get_audio_metadata_map_args(args)
    result += args.passthrough_args
    result += [common.get_safe_filename(title + '.' + args.container, args.always_number)]

    return result

# --------------------------------------------------------------------------------------------------
def get_log_command(args: Namespace, file_name: str) -> list[str]:
    """
    Returns the arguments to either delete or rename the pass one log file, as requested by the
    user in the script arguemnts.
    """
    title = os.path.splitext(os.path.basename(file_name))[0]
    if args.delete_log:
        return ['rm', f'{title}-0.log']
    else:
        return ['mv',
                f'{title}-0.log',
                f'{title}_{datetime.now():%Y%m%d-%H%M%S}.log']

# --------------------------------------------------------------------------------------------------
def process_segment(args: Namespace, segment: common.Segment, file_name: str) -> None:
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
def process_file(args: Namespace, file_name: str) -> None:
    """
    Executes the requested action for a single input file.
    """
    if args.segments is not None:
        for segment in args.segments:
            process_segment(args, common.Segment(segment[0], segment[1], None), file_name)
    else:
        process_segment(args, common.Segment(args.start, args.end, args.duration), file_name)

# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
     sys.exit(main())
