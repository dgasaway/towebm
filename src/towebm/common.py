# common.py - Shared routines.
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

import collections.abc
import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace
from collections import namedtuple

# --------------------------------------------------------------------------------------------------
Segment = namedtuple('Segment', 'start, end, duration')

# --------------------------------------------------------------------------------------------------
def get_safe_filename(filename: str, always_number: bool) -> str:
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
            s = f'{base}_{i:02}{ext}'
            if not os.path.exists(s):
                return s
        return filename

# --------------------------------------------------------------------------------------------------
def duration_to_seconds(duration: str) -> float:
    """
    Converts the specified ffmpeg duration string into a decimal representing the number of seconds
    represented by the duration string; None if the string is not parsable.
    """
    pattern = r'^((((?P<hms_grp1>\d*):)?((?P<hms_grp2>\d*):)?((?P<hms_secs>\d+([.]\d*)?)))|' \
              r'((?P<smu_value>\d+([.]\d*)?)(?P<smu_units>s|ms|us)))$'
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
def get_video_filter_args(args: Namespace, segment: Segment) -> list[str]:
    """
    Returns a list of ffmpeg arguments that apply all of the selected video filters requested in the
    specified script arguments, or an empty list if none apply.
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
        filters += [f'eq=gamma={args.gamma}']

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
        filters += [f'fade=t=in:st=0:d={args.fade_in}']
    if args.fade_out is not None:
        if segment.duration is not None:
            duration = duration_to_seconds(segment.duration)
        else:
            start = 0.0 if segment.start is None else duration_to_seconds(segment.start)
            duration = duration_to_seconds(segment.end) - start
        filters += [f'fade=t=out:st={duration - args.fade_out}:d={args.fade_out}']

    if args.filter is not None:
        for filter in args.filter:
            filters += [filter]

    if len(filters) == 0:
        filters = ['copy']

    return ['-filter_complex', '[0:v]' + ','.join(filters)]

# --------------------------------------------------------------------------------------------------
def get_audio_filters(args: Namespace, segment: Segment) -> list[str]:
    """
    Returns a list of audio filters, one element per standard filter or user argument.
    """
    filters = []

    # Want to apply standard filters is a certain order, so do not loop.
    if args.volume != 1.0:
        filters += [f'volume={args.volume}']

    # The fade filters take a start time relative to the start of the output, rather than the start
    # of the source.  So, fade in will start at 0 secs.  Fade out needs to get the output duration
    # and subtract the fade out duration.
    if args.fade_in is not None:
        filters += [f'afade=t=in:st=0:d={args.fade_in}']
    if args.fade_out is not None:
        if segment.duration is not None:
            duration = duration_to_seconds(segment.duration)
        else:
            start = 0.0 if segment.start is None else duration_to_seconds(segment.start)
            duration = duration_to_seconds(segment.end) - start
        filters += [f'afade=t=out:st={duration - args.fade_out}:d={args.fade_out}']

    if args.audio_filter is not None:
        for filter in args.audio_filter:
            filters += [filter]

    return filters

# --------------------------------------------------------------------------------------------------
def get_audio_filter_args(args: Namespace, segment: Segment) -> list[str]:
    """
    Returns a list of ffmpeg arguments that apply all of the selected audio filters requested in the
    specified script arguments, or an empty list if none apply.
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
            per_track_filters.append(f'[0:a:{i}]' + ','.join(flts))

    if len(per_track_filters) == 0:
        return []
    else:
        return ['-filter_complex', ';'.join(per_track_filters)]

# --------------------------------------------------------------------------------------------------
def get_segment_arguments(segment: Segment) -> list[str]:
    """
    Returns a list of ffmepg arguments to select a portion of the input as requested by the user in
    the specified segment, or an empty list if none apply.
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
def get_audio_quality_arg(quality: float, stream_index: int | None=None) -> list[str]:
    """
    Returns a list of ffmpeg arguments for a specified audio quality and optional output stream
    index.
    """
    if isinstance(quality, float):
        if stream_index is None:
            arg = '-q:a'
        else:
            arg = f'-q:a:{stream_index}'
        return [arg, str(quality)]
    else:
        if stream_index is None:
            arg = '-b:a'
        else:
            arg = f'-b:a:{stream_index}'
        return [arg, f'{quality}k']

# --------------------------------------------------------------------------------------------------
def get_audio_quality_args(args: Namespace) -> list[str]:
    """
    Returns a list of one or more sets of ffmpeg audio quality arguments based on the audio quality
    arguments in the specified script arguments.
    """
    # We only output a quality for non-zero values, and since the stream index is the output index,
    # we can use the index of a filtered list.
    result = []
    for i, quality in enumerate([q for q in args.audio_quality if q is not None and q > 0]):
        result += get_audio_quality_arg(quality, i)
    return result

# --------------------------------------------------------------------------------------------------
def get_audio_metadata_map_arg(output_index: int=0, input_index: int | None=None) -> list[str]:
    """
    Returns a list two ffmpeg arguments for copying audio stream metadata from a specified source
    index to a specified output stream index.
    """
    arg = f'-map_metadata:s:a:{output_index}'
    if input_index is None:
        return [arg, '0:s:a']
    else:
        return [arg, f'0:s:a:{input_index}']

# --------------------------------------------------------------------------------------------------
def get_audio_metadata_map_args(args: Namespace) -> list[str]:
    """
    Returns a list of ffmpeg arguments to copy audio metadata from the input streams to the matching
    output streams.
    """
    result: list[str] = []
    if isinstance(args.audio_quality, collections.abc.Sequence):
        # We need both the input and output index to create the map.
        output_index = 0
        for input_index, quality in enumerate(args.audio_quality):
            if quality is not None and quality > 0:
                result += get_audio_metadata_map_arg(output_index, input_index)
                output_index += 1
    elif args.audio_quality > 0:
        result = get_audio_metadata_map_arg()
    return result
