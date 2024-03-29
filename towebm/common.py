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
import sys
import argparse
from collections import namedtuple
from collections.abc import Sequence
import textwrap
from towebm._version import __version__

Segment = namedtuple('Segment', 'start, end, duration')

# --------------------------------------------------------------------------------------------------
class MultilineFormatter(argparse.HelpFormatter):
    """
    An argparse help formatter that supports using the token '|n ' to introduce newlines.
    """
    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        paragraphs = text.split('|n ')
        multiline_text = ''
        for paragraph in paragraphs:
            formatted_paragraph = textwrap.fill(
                paragraph, width, initial_indent=indent, subsequent_indent=indent) + '\n\n'
            multiline_text = multiline_text + formatted_paragraph
        return multiline_text

# --------------------------------------------------------------------------------------------------
class DelimitedValueAction(argparse.Action):
    """
    An argparse action that splits a list of colon-deparated values into a sequence.
    """
    def __init__(self, option_strings, dest, value_type=str, delimiter=':', value_choices=None,
        nargs=None, type=None, choices=None, **kwargs):
        if nargs is not None:
            raise ValueError('nargs not allowed')
        if type is not None:
            raise ValueError('use value_type')
        if choices is not None:
            raise ValueError('use value_choices')
        self._value_type = value_type
        self._delimiter = delimiter
        self._value_choices = value_choices
        
        super().__init__(option_strings, dest, type=type, **kwargs)

    def __call__(self, parser, ns, values, option_string=None):
        try:
            result = [None if s == '' else self._value_type(s)
                for s in values.split(self._delimiter)]
        except:
            raise argparse.ArgumentError(self,
                "must be a list of {} values delimited by '{}'".format(
                self._value_type.__name__, self._delimiter))

        if result is not None and self._value_choices is not None:
            for bad_choice in [choice for choice in result
                if choice is not None and choice not in self._value_choices]:
                raise argparse.ArgumentError(self,
                    "invalid choice: '{}' (choose from {})".format(
                        bad_choice, self._value_choices
                    ))
        setattr(ns, self.dest, result)

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
        action='count', default=0)

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
def add_passthrough_arguments(parser):
    """
    Adds passthrough argument help to a parser.
    """
    group = parser.add_argument_group('passthrough arguments',
        'Additional arguments can be passed to ffmpeg as-is before the output file name by adding '
        'an ''--'' argument followed by the ffmpeg arguments.  Note, because these preceed the '
        'output file name, they are only useful for output arguments.|n |n '
        '-- [arg [arg ...]]')

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
    elif args.deinterlace == 'selframe':
        filters += ['fieldmatch', 'bwdif=0:-1:1']
    
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

    if len(filters) == 0:
        filters = ['copy']

    return ['-filter_complex', '[0:v]' + ','.join(filters)]

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
    filters = get_audio_filters(args, segment)
    per_track_filters = []

    # We need to specify the input index for each that audio stream that will be output.  So, we
    # iterate the list with index, rather than use list comprehension.
    for i, quality in enumerate(args.audio_quality):
        if quality is not None and quality > 0:
            # channel_layout_fix is going to use the same index, but it may have fewer values
            # specified than audio_quality.
            map_fix = (
                hasattr(args, 'channel_layout_fix') and
                i < len(args.channel_layout_fix) and
                args.channel_layout_fix[i] is not None and
                args.channel_layout_fix[i] != '0')
            if map_fix and (args.channel_layout_fix[i] == '5.1'):
                flts = ['channelmap=channel_layout=5.1'] + filters
            elif map_fix and args.channel_layout_fix[i] == '5.0':
                flts = ['pan=5.1|FR=FR|FL=FL|FC=FC|BL=SL|BR=SR'] + filters
            elif map_fix and args.channel_layout_fix[i] == '4.1':
                flts = ['pan=5.1|FR=FR|FL=FL|FC=FC|BL=BC|BR=BC|LFE=LFE'] + filters
            elif len(filters) == 0:
                flts = ['acopy']
            else:
                flts = filters
            per_track_filters.append('[0:a:{0}]'.format(i) + ','.join(flts))

    if len(per_track_filters) == 0:
        return []
    else:
        return ['-filter_complex', ';'.join(per_track_filters)]

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
    # We only output a quality for non-zero values, and since the stream index is the output index,
    # we can use the index of a filtered list.
    result = []
    for i, quality in enumerate([q for q in args.audio_quality if q is not None and q > 0]):
        result += get_audio_quality_arg(quality, i)
    return result

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
    if isinstance(args.audio_quality, Sequence):
        # We need both the input and output index to create the map.
        result = []
        output_index = 0
        for input_index, quality in enumerate(args.audio_quality):
            if quality is not None and quality > 0:
                result += get_audio_metadata_map_arg(output_index, input_index)
                output_index += 1
        return result
    elif args.audio_quality > 0:
        return get_audio_metadata_map_arg()

# --------------------------------------------------------------------------------------------------
def parse_args(parser):
    """
    Parses the command arguments; anything after a '--' argument is taken as a passthrough argument,
    while anything before is parsed using the given argparse parser.  The passthrough arguments are
    added to the result args as 'passthrough_args'.
    """
    argv = sys.argv[1:]
    idx = argv.index('--') if '--' in argv else -1
    pargs = argv[idx + 1:] if idx >= 0 else []
    argv = argv[:idx] if idx >= 0 else argv
    args = parser.parse_args(argv)
    args.passthrough_args = pargs
    return args
    
