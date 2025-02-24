# argparsers.py - Argument parser classes.
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
import re
import sys
from argparse import Action, ArgumentError, ArgumentParser, Namespace, _ArgumentGroup
from dataclasses import dataclass, field
from typing import Any, Sequence

from towebm.formats import Container, AudioQualityType, AudioFormat, VideoFormat
from towebm._version import __version__

# --------------------------------------------------------------------------------------------------
@dataclass
class Segment:
    """
    Represents a segment of the input file bound by ffmpeg duration strings.
    """
    start_str: str | None
    """
    An ffmpeg duration string specifying the start of the segment.
    """
    end_str: str | None
    """
    An ffmpeg duration string specifying the end of the segment.
    """
    duration_str: str | None
    """
    An ffmpeg duration string specifying the duration of the segment.
    """
    start: float = field(init=False)
    """
    The start position of the segment in seconds.
    """
    end: float | None = field(init=False)
    """
    The end position of the segment in seconds.
    """
    duration: float | None = field(init=False)
    """
    The duration of the segment in seconds.
    """
    def __post_init__(self):
        """
        Parse the `start_str`, `end_str`, and `duration_str` values to `start`, `end`, and
        `duration`, respectively.
        """
        self.start = 0.0 if self.start_str is None else Segment.duration_to_seconds(self.start_str)
        if self.end_str is not None:
            self.end = Segment.duration_to_seconds(self.end_str)
            self.duration = self.end - self.start
        elif self.duration_str is not None:
            self.duration = Segment.duration_to_seconds(self.duration_str)
            self.end = self.start + self.duration
        else:
            self.duration = None
            self.end = None

    # ----------------------------------------------------------------------------------------------
    @staticmethod
    def duration_to_seconds(duration: str) -> float | None:
        """
        Convert the specified ffmpeg duration string into a decimal representing the number of
        seconds represented by the duration string; None if the string is not parsable.
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
class DelimitedValueAction(Action):
    """
    An argparse action that splits a list of colon-separated values into a sequence.
    """
    def __init__(self,
        option_strings: Sequence[str],
        dest: str,
        value_type: type=str,
        delimiter: str=':',
        value_choices: Sequence[Any] | None=None,
        nargs=None,
        type=None,
        choices=None,
        **kwargs):

        if nargs is not None:
            msg = 'nargs not allowed'
            raise ValueError(msg)
        if type is not None:
            msg = 'use value_type'
            raise ValueError(msg)
        if choices is not None:
            msg = 'use value_choices'
            raise ValueError(msg)
        self._value_type = value_type
        self._delimiter = delimiter
        self._value_choices = value_choices

        super().__init__(option_strings, dest, type=type, **kwargs)

    # ----------------------------------------------------------------------------------------------
    def __call__(self, parser, ns, values, option_string=None):
        try:
            result = [None if s == '' else self._value_type(s)
                for s in values.split(self._delimiter)]
        except ValueError as ex:
            type_name = self._value_type.__name__
            msg = f"values must be a list of {type_name} values delimited by '{self._delimiter}'"
            raise ArgumentError(self, msg) from ex

        if result is not None and self._value_choices is not None:
            for bad_choice in [choice for choice in result
                if choice is not None and choice not in self._value_choices]:
                    msg = f"invalid choice: '{bad_choice}' (choose from {self._value_choices})"
                    raise ArgumentError(self, msg)
        setattr(ns, self.dest, result)

# --------------------------------------------------------------------------------------------------
class ExtraArgumentParser(ArgumentParser):
    """
    An `argparse.ArgumentParser` subclass that supports a series of arguments which are not parsed.
    """
    def parse_args(
        self,
        args: Sequence[str] | None=None,
        namespace=None,
        marker: str='--',
        dest: str | None=None) -> Namespace:
        """
        Convert argument strings to objects and assign them as attributes of the namespace.  Assign
        arguments after the specified marker to the specified destination.  Return the populated
        namespace.
        """
        # Use default if there is no marker or destination.
        if marker is None or dest is None:
            return super().parse_args(None, namespace)

        # Use default if there is no marker present.
        largs = sys.argv[1:] if args is None else args
        if largs is None or marker not in largs:
            return super().parse_args(None, namespace)

        # Grab all the arguments after the marker arg.
        idx = largs.index(marker)
        unparsed = largs[idx + 1:]

        # Give the base class the rest and assign unparsed args to destination.
        parsed = super().parse_args(largs[:idx], namespace)
        vars(parsed)[dest] = unparsed

        return parsed

# --------------------------------------------------------------------------------------------------
class ConverterArgumentParser(ExtraArgumentParser):
    """
    A `PassthroughArgumentParser` subclass that adds methods for adding shared arguments for
    converter tools in this package.
    """
    def __init__(self, description: str | None):
        """
        Construct an instance with the specified description.
        """
        super().__init__(description=description, fromfile_prefix_chars='@')
        self._has_passthrough_arguments = False
        self._containers : list[Container] = []

    # ----------------------------------------------------------------------------------------------
    def add_basic_arguments(self, group: _ArgumentGroup | None=None) -> None:
        """
        Add basic arguments that apply to all converter tools.
        """
        parent = self if group is None else group
        parent.add_argument('--version', action='version', version='%(prog)s ' + __version__)
        parent.add_argument('-#', '--always-number',
            help='always add a number to the output file name',
            action='store_true', default=False)
        parent.add_argument('--pretend',
            help='display command lines but do not execute',
            action='store_true')
        parent.add_argument('-v', '--verbose',
            help='verbose output',
            action='count', default=0)
        parent.add_argument('source_files',
            help='source files to convert',
            action='store', metavar='source_file', nargs='+')

    # ----------------------------------------------------------------------------------------------
    def add_audio_quality_argument(
            self, format: AudioFormat, group: _ArgumentGroup | None=None) -> None:
        """
        Add an argument quality argument for the specified audio format.
        """
        parent = self if group is None else group
        if format.quality_type == AudioQualityType.QUALITY:
            text = f'audio quality (default {format.default_quality})'
            value_type = float
        elif format.quality_type == AudioQualityType.COMP_LEVEL:
            text = f'compression level (default {format.default_quality})'
            value_type = int
        else:
            text = f'audio bitrate in kbps (default {format.default_quality})'
            value_type = int
        text += (
            '; a colon-delimited list where each index matches a source audio track; a zero or '
            'blank value ignores a source track'
        )
        multi = len([c for c in format.containers if c.supports_multiple_tracks])
        if multi > 0:
            text += '; '
            if multi < len(format.containers):
                text += 'depending on container format, '
            text += 'multiple non-zero values may be provided to convert multiple tracks'

        parent.add_argument(
            f'-{format.quality_type.name[0].lower()}',
            f'--{format.quality_type.name.lower()}',
            help=text,
            action=DelimitedValueAction,
            dest='audio_quality',
            metavar=format.quality_type.name,
            value_type=value_type,
            default=[format.default_quality])

    # ----------------------------------------------------------------------------------------------
    def add_timecode_arguments(self, group: _ArgumentGroup | None=None) -> None:
        """
        Add time code arguments (--start, --end, --duration, --segment).
        """
        parent = self if group is None else group
        parent.add_argument('--start',
            help='starting source position',
            action='store')
        parent.add_argument('--duration',
            help='duration to encode',
            action='store')
        parent.add_argument('--end',
            help='ending source position',
            action='store')
        parent.add_argument('--segment',
            help='segment start and end source position; may be specified multiple times to encode '
                'multiple segments to separate files; enables --always-number when specified more '
                'than once',
            nargs=2, metavar=('START', 'END'), action='append', dest='segments')

    # ----------------------------------------------------------------------------------------------
    def add_timecode_argument_group(self) -> _ArgumentGroup:
        """
        Add a new group containing time code arguments (--start, --end, --duration, --segment) and
        return the group.
        """
        group = self.add_argument_group('source segment arguments',
            'A single segment or multiple segments of a source file may be encoded using the '
            'following arguments.  The first three may be used independently or combined, while '
            'the  last not not be combined with the first three.  The same arguments will be '
            'applied to  all source files.  All argument values are in ffmpeg duration format; see '
            'ffmpeg documentation for more details.')
        self.add_timecode_arguments(group)
        return group

    # ----------------------------------------------------------------------------------------------
    def add_fade_arguments(self, group: _ArgumentGroup | None=None) -> None:
        """
        Add --fade-in and --fade-out arguments.
        """
        parent = self if group is None else group
        parent.add_argument('--fade-in',
            help='apply a fade-in at the start of each output',
            action='store', type=float, metavar='SECONDS')
        parent.add_argument('--fade-out',
            help='apply a fade-out at the end of each output',
            action='store', type=float, metavar='SECONDS')

    # ----------------------------------------------------------------------------------------------
    def add_channel_layout_fix_argument(self, group: _ArgumentGroup | None=None) -> None:
        """
        Add a --channel-layout-fix argument.
        """
        parent = self if group is None else group
        parent.add_argument('--channel-layout-fix',
            help='apply a channel layout fix to 4.1, 5.0, 5.1(side) audio sources to output a '
                'compatible 5.1(rear) layout; may be a colon-delimited list to apply the fix to '
                'multiple audio tracks from the source; choices are 4.1, 5.0, 5.1; 0 or blank '
                'apply no fix',
            action=DelimitedValueAction, metavar="FIX_STRING",
            value_choices=['0', '4.1', '5.0', '5.1'], default=['0'])

    # ----------------------------------------------------------------------------------------------
    def add_audio_filter_arguments(
            self, format: AudioFormat, group: _ArgumentGroup | None=None) -> None:
        """
        Add audio filter arguments.
        """
        parent = self if group is None else group
        parent.add_argument('--volume',
            help='amplitude (volume) multiplier, < 1.0 to reduce volume, or > 1.0 to increase '
                'volume; recommended to use replaygain to tag the file post-conversion, instead',
            action='store', type=float, default=1.0)
        parent.add_argument('-af', '--audio-filter',
            help='custom audio filter, passed as -af argument to ffmpeg',
            action='append', dest='audio_filter')
        if format.requires_channel_layout_fix:
            self.add_channel_layout_fix_argument(parent)

    # ----------------------------------------------------------------------------------------------
    def add_passthrough_argument_group(self) -> _ArgumentGroup:
        """
        Add a new group containing a dummy passthrough argument and return the group.
        """
        # Add a group with additional explanation.
        group = self.add_argument_group('passthrough arguments',
            'Additional arguments can be passed to ffmpeg as-is before the output file name by '
            'adding an ''--'' argument followed by the ffmpeg arguments.  Note, because these '
            'preceed the output file name, they are only useful for output arguments.  Must appear '
            'as the final arguments.')

        # Add a dummy argument that defines a destination and adds help/usage text.  We will pull
        # this and following arguments from those passed to the base class.  Unfortunately, the
        # usage text will show this before any positional arguments.
        group.add_argument('--',
            help='passthrough output arguments',
            dest='passthrough_args', metavar='ARG', nargs='*', default=[])

        self._has_passthrough_arguments = True
        return group

    # ----------------------------------------------------------------------------------------------
    def add_container_argument(
            self, containers: Sequence[Container], group: _ArgumentGroup | None=None ) -> None:
        """
        Add an argument for selection of the container format.
        """
        self._containers = containers
        if len(containers) > 1:
            parent = self if group is None else group
            choices = [c.name for c in containers]
            parent.add_argument('-C', '--container',
                help=f'container format (default {choices[0]})',
                action='store', choices=choices, default=choices[0])

    # ----------------------------------------------------------------------------------------------
    def _check_timecode_arguments(self, args: Namespace) -> None:
        """
        Raise a parser error if the specified args contain an invalid combination of arguments
        added by `add_timecode_arguments()`.  Sets `always_number` if any --segment arguments.
        """
        if ('duration' in args and args.duration is not None and
            'end' in args and args.end is not None):
            self.error('--duration and --end may not be used together')

        if 'segments' in args and args.segments is not None:
            if (('start' in args and args.start is not None) or
                ('duration' in args and args.duration is not None) or
                ('end' in args and args.end is not None)):
                self.error('--segments may not be used with other segment selectors')
            if len(args.segments) > 1:
                args.always_number = True

        if 'fade_out' in args and args.fade_out is not None:
            if not (('duration' in args and args.duration is not None) or
                ('end' in args and args.end is not None) or
                ('segments' in args and args.segments is not None)):
                self.error('--fade-out requires --duration, --end, or --segment')

    # ----------------------------------------------------------------------------------------------
    def _check_source_files_exist(self, source_files: Sequence[str]) -> None:
        """
        Raise a parser error if the specified list contains an element that is not an existing
        file.
        """
        for source_file in source_files:
            if not os.path.exists(source_file) or not os.path.isfile(source_file):
                self.error('invalid source file: ' + source_file)

    # ----------------------------------------------------------------------------------------------
    def parse_args(self, args: Sequence[str] | None=None, namespace=None) -> Namespace:
        """
        Convert argument strings to objects and assign them as attributes of the namespace.  Return
        the populated namespace.
        """
        dest = 'passthrough_args' if self._has_passthrough_arguments else None
        parsed = super().parse_args(args, namespace, dest=dest)
        self._check_timecode_arguments(parsed)

        # Add/replace `container` with the original Container instance from _containers.
        if (len(self._containers) == 1):
            parsed.container = self._containers[0]
        else:
            parsed.container = next(f for f in self._containers if f.name == parsed.container)

        # Create an `all_segments` containing Segment instances representing all timecode args.
        if parsed.segments is not None:
            parsed.all_segments = [Segment(s[0], s[1], None) for s in parsed.segments]
        else:
            parsed.all_segments = [Segment(parsed.start, parsed.end, parsed.duration)]

        if 'source_files' in parsed and parsed.source_files is not None:
            self._check_source_files_exist(parsed.source_files)

        return parsed

# --------------------------------------------------------------------------------------------------
class AudioConverterArgumentParser(ConverterArgumentParser):
    """
    A `ConverterArgumentParser` subclass for audio converter tools.
    """
    def __init__(self, audio_format: AudioFormat):
        """
        Construct an argument parser pre-populated with arguments for an audio converter tool that
        outputs the specified format.
        """
        self.audio_format = audio_format
        desc = f'Converts audio/video files to audio-only {audio_format.name} using ffmpeg'
        super().__init__(desc)

        # Options group
        self.add_basic_arguments()
        self.add_audio_quality_argument(audio_format)

        # Note: This may not add an argument if there is only one container chice, but we need to
        # call it anyway.
        self.add_container_argument(audio_format.containers)

        # Timecode group
        self.add_timecode_argument_group()

        # Filter group
        group = self.add_argument_group('filter arguments')
        self.add_fade_arguments(group)
        self.add_audio_filter_arguments(audio_format, group)

        # Passthrough
        self.add_passthrough_argument_group()

    # ----------------------------------------------------------------------------------------------
    def parse_args(self, args: Sequence[str] | None=None, namespace=None) -> Namespace:
        """
        Convert argument strings to objects and assign them as attributes of the namespace.  Return
        the populated namespace.
        """
        parsed = super().parse_args(args, namespace)

        qual_name = self.audio_format.quality_type.name
        if parsed.container.supports_multiple_tracks:
            if len([q for q in parsed.audio_quality if q is not None and q > 0]) < 1:
                msg = f'at least one positive audio {qual_name} must be specified'
                self.error(msg)
        elif len([q for q in parsed.audio_quality if q is not None and q > 0]) != 1:
            msg = f'exactly one non-zero {qual_name} must be specified for the container'
            self.error(msg)

        return parsed

# --------------------------------------------------------------------------------------------------
class VideoConverterArgumentParser(ConverterArgumentParser):
    def __init__(self, video_format: VideoFormat):
        """
        Construct an argument parser pre-populated with arguments for a video converter tool that
        outputs the specified format.
        """
        self.video_format = video_format
        s = ' or '.join([f.name for f in video_format.containers])
        desc = (
            f'Converts video files to {video_format.name} + '
            f'{video_format.audio_format.name} in a {s} container using a '
            f'{len(video_format.passes)}-pass ffmpeg encode.'
        )
        super().__init__(desc)

        # Options group
        self.add_basic_arguments()
        self.add_video_quality_argument()
        self.add_audio_quality_argument(video_format.audio_format)

        # Note: This may not add an argument if there is only one container chice, but we need to
        # call it anyway.
        self.add_container_argument(video_format.containers)

        # Add arguments only needed if more than one pass.  Note: 'pass' is a keyword, so
        # 'pass_num' is used internally.
        if len(video_format.passes) > 1:
            self.add_multi_pass_arguments(video_format.passes)

        # Timecode group.
        self.add_timecode_argument_group()

        # Video filter group.
        group = self.add_argument_group('video filter arguments',
            'The deinterlate filter is applied first; standard crop filters (e.g., "-s crop43") are '
            'applied before custom crop values (e.g., "-x 10 10"); crop filters are applied before '
            'scale filters (e.g., "-s scale23");  and all standard filters are applied before custom '
            '-vf filters.')
        self.add_video_filter_arguments(group)

        # Audio filter group.
        group = self.add_argument_group('audio filter arguments')
        self.add_audio_filter_arguments(video_format.audio_format, group)

        # Passthrough
        self.add_passthrough_argument_group()

    # ----------------------------------------------------------------------------------------------
    def add_video_quality_argument(self, group: _ArgumentGroup | None=None):
        parent = self if group is None else group
        s = f'{self.video_format.video_quality_help} (default {self.video_format.default_quality})'
        parent.add_argument('-q', '--quality',
            help=s, action='store', type=int, default=self.video_format.default_quality)

    # ----------------------------------------------------------------------------------------------
    def add_video_filter_arguments(self, group: _ArgumentGroup | None=None):
        parent = self if group is None else group
        parent.add_argument('-s', '--standard-filter',
            help='standard video/audio filter; '
                '[crop43] crops horizontally to 4:3 aspect ratio; '
                '[scale23] scales down by 2/3 (e.g., 1080p to 720p); '
                '[gray] converts to grayscale',
            action='append', choices=['crop43', 'scale23', 'gray'])
        parent.add_argument('-d', '--deinterlace',
            help='deinterlate filter; '
                '[frame] output a frame from each pair of input fields; '
                '[field] output an interpolated frame from each input field; '
                '[ivtc] inverse telecine; '
                '[ivtc+] inverse telecine with fallback deinterlace; '
                '[selframe] selectively deinterlace frames ',
            action='store', choices=['frame', 'field', 'ivtc', 'ivtc+', 'selframe'])
        parent.add_argument('--parity',
            help='set a specific parity for the deinterlace filter; '
                '[tff] top field first; '
                '[bff] bottom field first',
            action='store', choices=['tff', 'bff'])

        self.add_fade_arguments(parent)

        parent.add_argument('-x', '--crop-width',
            help='left and right crop values',
            nargs=2, type=int, metavar=('LEFT', 'RIGHT'))
        parent.add_argument('-y', '--crop-height',
            help='top and bottom crop values',
            nargs=2, type=int, metavar=('TOP', 'BOTTOM'))
        parent.add_argument('-g', '--gamma',
            help='gramma correction (default 1.0; no correction)',
            action='store', type=float, default=1.0)
        parent.add_argument('-vf', '--video-filter',
            help='custom video filter, similar to -vf ffmpeg argument',
            action='append')

    # ----------------------------------------------------------------------------------------------
    def add_multi_pass_arguments(self, passes: list[int], group: _ArgumentGroup | None=None):
        """
        Add arguments that relate to a two-pass encode.
        """
        parent = self if group is None else group
        parent.add_argument('--pass',
            help='run only a given pass',
            action='store', choices=passes, dest='pass_num')
        parent.add_argument('--delete-log',
            help='delete pass 1 log (otherwise keep with timestamp)',
            action='store_true')
