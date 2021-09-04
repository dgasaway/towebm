# common.py - Shared routines.
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

import os
import re
from collections import namedtuple
from collections.abc import Sequence
from towebm._version import __version__

Segment = namedtuple('Segment', 'start, end, duration')

# --------------------------------------------------------------------------------------------------
def add_basic_arguments(parser):
    """
    Adds basic arguments that apply to all scripts to a parser.
    """
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('-#', '--always-number',
        help='always add a number to the output file name',
        action='store_true', default=False)
    parser.add_argument('--pretend',
        help='display command lines but do not execute',
        action='store_true')
    parser.add_argument('-v', '--verbose',
        help='verbose output',
        action='store_true')

# --------------------------------------------------------------------------------------------------
def add_timecode_arguments(parser):
    """
    Adds timecode arguments to a parser.
    """
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
        help='segment start and end source position; may be specified multiple times to encode '
             'multiple segments to separate files; enables --always-number when specified more '
             'than once',
        nargs=2, metavar=('START', 'END'), action='append', dest='segments')
    return sgroup

# --------------------------------------------------------------------------------------------------
def add_audio_filter_arguments(parser):
    """
    Adds filter arguments that apply to audio-only encodes to a parser.
    """
    fgroup = parser.add_argument_group('filter arguments')
    fgroup.add_argument('--fade-in',
        help='apply an audio fade-in at the start of each output',
        action='store', type=float, metavar='SECONDS')
    fgroup.add_argument('--fade-out',
        help='apply an audio fade-out at the end of each output',
        action='store', type=float, metavar='SECONDS')
    fgroup.add_argument('-f', '--filter',
        help='custom audio filter, passed as -af argument to ffmpeg',
        action='append', dest='audio_filter')
    fgroup.add_argument('--volume', 
        help='amplitude (volume) multiplier, < 1.0 to reduce volume, or > 1.0 to increase volume; '
             'recommended to use replaygain to tag the file post-conversion, instead',
        action='store', type=float, default=1.0)

# --------------------------------------------------------------------------------------------------
def check_timecode_arguments(parser, args):
    """
    Raises a parser error if args contains an invalid combination of --start, --end, --duration,
    and --segment.
    """
    # Check for invalid combinations.
    if args.duration is not None and args.end is not None:
        parser.error('--duration and --end may not be used together')
    if args.start is not None or args.duration is not None or args.end is not None:
        if args.segments is not None:
            parser.error('--segments may not be used with other segment selectors')
    if args.fade_out is not None:
        if args.duration is None and args.end is None and args.segments is None:
            parser.error('--fade-out requires --duration, --end, or --segment')

# --------------------------------------------------------------------------------------------------
def check_source_files_exist(parser, args):
    """
    Raises a parser error if args contains any source files that do not exist.
    """
    for source_file in args.source_files:
        if not os.path.exists(source_file):
            parser.error('invalid source file: ' + source_file)

# --------------------------------------------------------------------------------------------------
def get_safe_filename(filename, always_number):
    """
    Returns the source file name if no file exists with the given name and 'always_number' is false;
    returns the source file name with an understore and two-digit sequence number appended to make
    the file name unique if the source file name is not unique or 'always_number' is true; if no
    such file name is unique, returns the source file name.
    """
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
def duration_to_seconds(duration):
    """
    Converts an ffmpeg duration string into a decimal representing the number of seconds
    represented by the duration string; None if the string is not parsable.
    """
    pattern = r'^((((?P<hms_grp1>\d*):)?((?P<hms_grp2>\d*):)?((?P<hms_secs>\d+([.]\d*)?)))|' \
              '((?P<smu_value>\d+([.]\d*)?)(?P<smu_units>s|ms|us)))$'
    match = re.match(pattern, duration)
    if match:
        groups = match.groupdict()
        if groups['hms_secs'] is not None:
            value = float(groups['hms_secs'])
            if groups['hms_grp2'] is not None:
                value += int(groups['hms_grp1']) * 60 * 60 + int(groups['hms_grp2']) * 60
            elif groups['hms_grp1'] is not None:
                value += int(groups['hms_grp1']) * 60
        else:
            value = float(groups['smu_value'])
            units = groups['smu_units']
            if units == 'ms':
                value /= 1000.0
            elif units == 'us':
                value /= 1000000.0
        return value
    else:
        return None

# --------------------------------------------------------------------------------------------------
def get_video_filter_args(args, segment):
    """
    Returns a list of ffmpeg arguments that apply all of the selected video filters requested in the
    script arguments, or an empty list if none apply.
    """
    filters = []
    
    # Deinterlace first.
    parity = ''
    if args.parity is not None:
        parity = ':' + args.parity
    if args.deinterlace == 'frame':
        filters += ['bwdif=send_frame' + parity]
    elif args.deinterlace == 'field':
        filters += ['bwdif=send_field' + parity]
    elif args.deinterlace == 'ivtc':
        filters += ['fieldmatch', 'decimate']
    elif args.deinterlace == 'ivtc+':
        filters += ['fieldmatch', 'bwdif=send_frame', 'decimate']
    
    # Want to apply standard filters is a certain order, so do not loop.
    if args.standard_filter is not None:
        if 'gray' in args.standard_filter:
            filters += ['format=gray']
        if 'crop43' in args.standard_filter:
            filters += ['crop=w=(in_h*4/3)']

    if args.gamma != 1.0:
        filters += ['eq=gamma={g}'.format(g=args.gamma)]

    if args.crop_width is not None or args.crop_height is not None:
        if args.crop_width is not None and args.crop_height is not None:
            crop = 'crop=x={x[0]}:w=in_w-{x[0]}-{x[1]}:y={y[0]}:h=in_h-{y[0]}-{y[1]}'
        elif args.crop_width is not None:
            crop = 'crop=x={x[0]}:w=in_w-{x[0]}-{x[1]}'
        else:
            crop = 'crop=y={y[0]}:h=in_h-{y[0]}-{y[1]}'
        filters += [crop.format(x=args.crop_width, y=args.crop_height)]
    
    if args.standard_filter is not None:
        if 'scale23' in args.standard_filter:
            filters += ['scale=h=in_h*2/3:w=-1']
    
    # The fade filters take a start time relative to the start of the output, rather than the start
    # of the source.  So, fade in will start at 0 secs.  Fade out needs to get the output duration
    # and subtract the fade out duration.
    if args.fade_in is not None:
        filters += ['fade=t=in:st=0:d={0}'.format(args.fade_in)]
    if args.fade_out is not None:
        if segment.duration is not None:
            duration = duration_to_seconds(segment.duration)
        else:
            start = 0.0 if segment.start is None else duration_to_seconds(segment.start)
            duration = duration_to_seconds(segment.end) - start
        filters += ['fade=t=out:st={0}:d={1}'.format(duration - args.fade_out, args.fade_out)]
        
    if args.filter is not None:
        for filter in args.filter:
            filters += [filter]

    return ['-filter_complex', '[0:v]' + ','.join(filters)] if len(filters) > 0 else []

# --------------------------------------------------------------------------------------------------
def get_audio_filters(args, segment):
    """
    Returns a lits of audio filters, one element per standard filter or user argument.
    """
    filters = []
    
    # Want to apply standard filters is a certain order, so do not loop.
    if args.volume != 1.0:
        filters += ['volume={v}'.format(v=args.volume)]

    # The fade filters take a start time relative to the start of the output, rather than the start
    # of the source.  So, fade in will start at 0 secs.  Fade out needs to get the output duration
    # and subtract the fade out duration.
    if args.fade_in is not None:
        filters += ['afade=t=in:st=0:d={0}'.format(args.fade_in)]
    if args.fade_out is not None:
        if segment.duration is not None:
            duration = duration_to_seconds(segment.duration)
        else:
            start = 0.0 if segment.start is None else duration_to_seconds(segment.start)
            duration = duration_to_seconds(segment.end) - start
        filters += ['afade=t=out:st={0}:d={1}'.format(duration - args.fade_out, args.fade_out)]
        
    if args.audio_filter is not None:
        for filter in args.audio_filter:
            filters += [filter]

    return filters

# --------------------------------------------------------------------------------------------------
def get_audio_filter_args(args, segment):
    """
    Returns a list of ffmpeg arguments that apply all of the selected audio filters requested in the
    script arguments, or an empty list if none apply.
    """
    labels = []
    if isinstance(args.audio_quality, Sequence) and len(args.audio_quality) > 1:
        # We need to specify the input index for each that audio stream that will be output.
        for i, quality in enumerate(args.audio_quality):
            if quality > 0:
                labels += ['[0:a:{0}]'.format(i)]
    
    filters = get_audio_filters(args, segment)
    if len(labels) == 0 and len(filters) == 0:
        return []
    else:
        if len(labels) == 0: labels = ['[0:a]']
        if len(filters) == 0: filters = ['acopy']
        return ['-filter_complex', ';'.join([label + ','.join(filters) for label in labels])]

# --------------------------------------------------------------------------------------------------
def get_segment_arguments(segment):
    """
    Returns a list of ffmepg arguments to select a portion of the input as requested by the user in
    the script arguments, or an empty list if none apply.
    """
    result = []
    if segment.start is not None:
        result += ['-accurate_seek', '-ss', segment.start]
    if segment.end is not None:
        result += ['-to', segment.end]
    if segment.duration is not None:
        result += ['-t', segment.duration]
    return result

# --------------------------------------------------------------------------------------------------
def get_audio_quality_arg(quality, stream_index = None):
    """
    Returns a list two ffmpeg arguments for a given audio quality and optional output stream index.
    """
    result = []
    if isinstance(quality, float):
        if stream_index is None:
            arg = '-q:a'
        else:
            arg = '-q:a:{0}'.format(stream_index)
        return [arg, str(quality)]
    else:
        if stream_index is None:
            arg = '-b:a'
        else:
            arg = '-b:a:{0}'.format(stream_index)
        return [arg, '{0}k'.format(quality)]

# --------------------------------------------------------------------------------------------------
def get_audio_quality_args(args):
    """
    Returns a list of one or more sets of ffmpeg audio quality arguments based on the script audio
    quality arguments.
    """
    if isinstance(args.audio_quality, Sequence):
        if len(args.audio_quality) == 1:
            return get_audio_quality_arg(args.audio_quality[0])
        else:
            # We only output a quality for non-zero values, and since the stream index is the
            # output index, we can use the index of a filtered list.
            result = []
            for i, quality in enumerate([q for q in args.audio_quality if q > 0]):
                result += get_audio_quality_arg(quality, i)
            return result
    else:
        return get_audio_quality_arg(args.audio_quality)

# --------------------------------------------------------------------------------------------------
def get_audio_metadata_map_arg(output_index=0, input_index=None):
    """
    Returns a list two ffmpeg arguments for copying audio stream metadata from a source stream to an
    output stream.
    """
    arg = '-map_metadata:s:a:{0}'.format(output_index)
    if input_index is None:
        return [arg, '0:s:a']
    else:
        return [arg, '0:s:a:{0}'.format(input_index)]

# --------------------------------------------------------------------------------------------------
def get_audio_metadata_map_args(args):
    """
    Returns a list of ffmpeg arguments to copy audio metadata from the input streams to the matching
    output streams.
    """
    if isinstance(args.audio_quality, Sequence) and len(args.audio_quality) > 1:
        # We need both the input and output index to create the map.
        result = []
        output_index = 0
        for input_index, quality in enumerate(args.audio_quality):
            if quality > 0:
                result += get_audio_metadata_map_arg(output_index, input_index)
                output_index += 1
        return result
    else:
        return get_audio_metadata_map_arg()
