#!/usr/bin/python3

# towebm - Converts videos to webm format (vp9+opus) using ffmpeg.
# Copyright (C) 2021 David Gasaway
# https://bitbucket.org/dgasaway/towebm

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
from towebm._version import __version__

# --------------------------------------------------------------------------------------------------
def main():
    parser = ArgumentParser(
        description='Converts videos to webm format (vp9+opus) using a two-pass ffmpeg encode.',
        fromfile_prefix_chars="@")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('-q', '--quality',
        help='video quality (lower is better, default 30)',
        action='store', type=int, default=30)
    parser.add_argument('-b', '--audio-bitrate',
        help='audio bitrate in kbps (default 160)',
        action='store', type=int, default=160)

    # Note: 'pass' is a keyword, so used name 'only_pass' internally.
    parser.add_argument('--pass',
        help='run only a given pass',
        action='store', choices=['1', '2'], dest='only_pass')
    parser.add_argument('-#', '--always-number',
        help='always add a number to the output file name',
        action='store_true', default=False)
    parser.add_argument('--pretend',
        help='display command lines but do not execute',
        action='store_true')
    parser.add_argument('--delete-log',
        help='delete pass 1 log (otherwise keep with timestamp)',
        action='store_true')
    parser.add_argument('-v', '--verbose',
        help='verbose output',
        action='store_true')

    # Timecode/segment arguments.    
    sgroup = parser.add_argument_group('input segment arguments',
        'A single segment or multiple segments of the input file may be encoded using the '
        'following arguments.  The first three may be used independently or combined, while the '
        'last not not be combined with the first three.  The same arguments will be applied to '
        'all input files.  All argument values are in ffmpeg duration format; see ffmpeg '
        'documentation for more details.')
    sgroup.add_argument('--start',
        help='starting input position',
        action='store')
    sgroup.add_argument('--duration',
        help='duration to encode',
        action='store')
    sgroup.add_argument('--end',
        help='ending input position',
        action='store')
    sgroup.add_argument('--segment',
        help='segment start and end input position; my be specified multiple times to encode '
             'multiple segments to separate files; enables --always-number when specified more '
             'than once',
        nargs=2, metavar=('START', 'END'), action='append', dest='segments')

    # Video/audio filter arguments.
    fgroup = parser.add_argument_group('video/audio filter arguments',
        'Standard crop filters (e.g., "-s crop43") are applied before custom crop values '
        '(e.g., "-x 10 10"); crop filters are applied before scale filters (e.g., "-s scale23"); '
        'and all standard filters are applied before custom (i.e., "-f" and "-a") filters.')
    fgroup.add_argument('-s', '--standard-filter',
        help='standard video/audio filter; '
             '[crop43] crops horizontally to 4:3 aspect ratio; '
             '[scale23] scales down by 2/3 (e.g., 1080p to 720p); '
             '[gray] converts to grayscale; '
             '[deint] deinterlaces; '
             '[anorm] applies audio normalization',
        action='append', choices=['crop43', 'scale23', 'gray', 'deint', 'anorm'])
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
        help='custom video filter, passed as -vf argument to ffmpeg',
        action='append')
    fgroup.add_argument('-a', '--audio-filter',
        help='custom audio filter, passed as -af argument to ffmpeg',
        action='append')
    fgroup.add_argument('--volume', 
        help='amplitude (volume) multiplier, < 1.0 to reduce volume, or > 1.0 to increase volume',
        action='store', type=float, default=1.0)

    parser.add_argument('video_files',
        help='video files to convert',
        action='store', metavar='video_file', nargs='+')
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

    # Check for valid files.
    for video_file in args.video_files:
        if not os.path.exists(video_file):
            parser.error('invalid file: ' + video_file)

    ret = 0
    for file in args.video_files:
        try:
            process_file(args, file)
        except subprocess.CalledProcessError as e:
            if ret == 0 or e.returncode > ret:
                ret = e.returncode
            print('Execution error, proceeding to next input file.')
    exit(ret)

# --------------------------------------------------------------------------------------------------
def get_safe_filename(filename, always_number):
    if not always_number and not os.path.exists(filename):
        return filename
    else:
        (base, ext) = os.path.splitext(filename)
        for i in range(100):
            s = '{0}_{1:02}{2}'.format(base, i, ext)
            if not os.path.exists(s):
                return s
        return filename

# --------------------------------------------------------------------------------------------------
def append(s1, s2, delimit):
    if s1 != '':
        return s1 + delimit + s2
    else:
        return s2

# --------------------------------------------------------------------------------------------------
def build_video_filter(args):
    vf = ''

    # Want to apply standard filters is a certain order, so do not loop.
    if args.standard_filter is not None:
        if 'deint' in args.standard_filter:
            vf = append(vf, 'yadif=parity=tff', ',')
        if 'gray' in args.standard_filter:
            vf = append(vf, 'format=gray', ',')
        if 'crop43' in args.standard_filter:
            vf = append(vf, 'crop=w=(in_h*4/3)', ',')

    if args.gamma != 1.0:
        vf = append(vf, 'eq=gamma={g}'.format(g=args.gamma), ',')

    if args.crop_width is not None or args.crop_height is not None:
        if args.crop_width is not None and args.crop_height is not None:
            crop = 'crop=x={x[0]}:w=in_w-{x[0]}-{x[1]}:y={y[0]}:h=in_h-{y[0]}-{y[1]}'
        elif args.crop_width is not None:
            crop = 'crop=x={x[0]}:w=in_w-{x[0]}-{x[1]}'
        else:
            crop = 'crop=y={y[0]}:h=in_h-{y[0]}-{y[1]}'
        vf = append(vf, crop.format(x=args.crop_width, y=args.crop_height), ',')
    
    if args.standard_filter is not None:
        if 'scale23' in args.standard_filter:
            vf = append(vf, 'scale=h=in_h*2/3:w=-1', ',')
    
    if args.filter is not None:
        for filter in args.filter:
            vf = append(vf, filter, ',')

    return ' -vf "' + vf + '"' if vf != '' else ''

# --------------------------------------------------------------------------------------------------
def build_audio_filter(args):
    af = ''

    # Want to standard filters is a certain order, so do not loop.
    if args.standard_filter is not None:
        if 'anorm' in args.standard_filter:
            af = append(af, 'dynaudnorm=g=301:r=0.9', ',')

    if args.volume != 1.0:
        af = append(af, 'volume={v}'.format(v=args.volume), ',')

    if args.audio_filter is not None:
        for filter in args.audio_filter:
            af = append(af, filter, ',')

    return ' -af "' + af + '"' if af != '' else ''

# --------------------------------------------------------------------------------------------------
def build_pass1_command(args, start, end, duration, file):
    fmt = (
        'ffmpeg -nostdin -hide_banner'
        '{start_arg}{duration_arg}{end_arg}'
        ' -i "{file}"'
        ' -c:v libvpx-vp9'
        ' -crf {args.quality}'
        ' -b:v 0'
        ' -tile-columns 2'
        ' -row-mt 1'
        ' -auto-alt-ref 1'
        ' -lag-in-frames 25'
        ' -pix_fmt yuv420p'
        '{vf_arg}'
        ' -an'
        ' -f webm'
        ' -threads 8'
        ' -pass 1'
        ' -passlogfile "{title}"'
        ' -cpu-used 4'
        ' -y'
        ' /dev/null')
    title = os.path.splitext(os.path.basename(file))[0]
    vf_arg = build_video_filter(args)
    start_arg = ' -accurate_seek -ss {0}'.format(start) if start is not None else ''
    duration_arg = ' -t {0}'.format(duration) if duration is not None else ''
    end_arg = ' -to {0}'.format(end) if end is not None else ''
    return fmt.format(
        file=file, args=args, vf_arg=vf_arg, start_arg=start_arg, duration_arg=duration_arg,
        end_arg=end_arg, title=title)

# --------------------------------------------------------------------------------------------------
def build_pass2_command(args, start, end, duration, file):
    fmt = (
        'ffmpeg -nostdin -hide_banner'
        '{start_arg}{duration_arg}{end_arg}'
        ' -i "{file}"'
        ' -c:v libvpx-vp9'
        ' -crf {args.quality}'
        ' -b:v 0'
        ' -tile-columns 2'
        ' -row-mt 1'
        ' -auto-alt-ref 1'
        ' -lag-in-frames 25'
        ' -pix_fmt yuv420p'
        '{vf_arg}'
        ' -c:a libopus'
        ' -b:a {args.audio_bitrate}k'
        '{af_arg}'
        ' -f webm'
        ' -threads 8'
        ' -pass 2'
        ' -passlogfile "{title}"'
        ' -cpu-used 2'
        ' -metadata title="{title}"'
        ' "{out_file}"')
    title = os.path.splitext(os.path.basename(file))[0]
    vf_arg = build_video_filter(args)
    af_arg = build_audio_filter(args)
    start_arg = ' -accurate_seek -ss {0}'.format(start) if start is not None else ''
    duration_arg = ' -t {0}'.format(duration) if duration is not None else ''
    end_arg = ' -to {0}'.format(end) if end is not None else ''
    out_file = get_safe_filename(title + '.webm', args.always_number)
    return fmt.format(
        file=file, out_file=out_file, args=args, vf_arg=vf_arg, af_arg=af_arg, start_arg=start_arg,
        duration_arg=duration_arg, end_arg=end_arg, title=title)

# --------------------------------------------------------------------------------------------------
def build_log_cmd(args, file):
    title = os.path.splitext(os.path.basename(file))[0]
    if args.delete_log:
        return 'rm "{0}-0.log"'.format(title)
    else:
        return 'mv "{0}-0.log" "{0}_{1:%Y%m%d-%H%M%S}.log"'.format(title, datetime.now())

# --------------------------------------------------------------------------------------------------
def process_segment(args, start, end, duration, file):
    if args.only_pass is None or args.only_pass == '1':
        pass1cmd = build_pass1_command(args, start, end, duration, file)
        if args.pretend or args.verbose >= 1:
            print(pass1cmd)
        if not args.pretend:
            subprocess.check_call(pass1cmd, shell=True)
    if args.only_pass is None or args.only_pass == '2':
        pass2cmd = build_pass2_command(args, start, end, duration, file)
        logcmd = build_log_cmd(args, file)
        if args.pretend or args.verbose >= 1:
            print(pass2cmd)
        if not args.pretend:
            subprocess.check_call(pass2cmd, shell=True)
        if args.pretend or args.verbose >= 1:
            print(logcmd)
        if not args.pretend:
            subprocess.check_call(logcmd, shell=True)
    
# --------------------------------------------------------------------------------------------------
def process_file(args, file):
    if args.segments is not None:
        for segment in args.segments:
            process_segment(args, segment[0], segment[1], None, file)
    else:
        process_segment(args, args.start, args.end, args.duration, file)

# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
