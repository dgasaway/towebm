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
import sys
from argparse import Action, ArgumentError, ArgumentParser, Namespace, _ArgumentGroup
from typing import Any, Sequence

from towebm._version import __version__


# --------------------------------------------------------------------------------------------------
class DelimitedValueAction(Action):
    """
    An argparse action that splits a list of colon-deparated values into a sequence.
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
            raise ValueError('nargs not allowed')
        if type is not None:
            raise ValueError('use value_type')
        if choices is not None:
            raise ValueError('use value_choices')
        self._value_type = value_type
        self._delimiter = delimiter
        self._value_choices = value_choices

        super().__init__(option_strings, dest, type=type, **kwargs)

    # ----------------------------------------------------------------------------------------------
    def __call__(self, parser, ns, values, option_string=None):
        try:
            result = [None if s == '' else self._value_type(s)
                for s in values.split(self._delimiter)]
        except:
            type_name = self._value_type.__name__
            msg = f"must be a list of {type_name} values delimited by '{self._delimiter}'"
            raise ArgumentError(self, msg)

        if result is not None and self._value_choices is not None:
            for bad_choice in [choice for choice in result
                if choice is not None and choice not in self._value_choices]:
                raise ArgumentError(self,
                    f"invalid choice: '{bad_choice}' (choose from {self._value_choices})")
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
class ToolArgumentParser(ExtraArgumentParser):
    """
    A `PassthroughArgumentParser` sublass that adds methods for adding shared arguments for tools
    in this package.
    """
    _has_passthrough_arguments = False

    # ----------------------------------------------------------------------------------------------
    def add_basic_arguments(self) -> None:
        """
        Add basic arguments that apply to all conversion scripts.
        """
        self.add_argument('--version', action='version', version='%(prog)s ' + __version__)
        self.add_argument('-#', '--always-number',
            help='always add a number to the output file name',
            action='store_true', default=False)
        self.add_argument('--pretend',
            help='display command lines but do not execute',
            action='store_true')
        self.add_argument('-v', '--verbose',
            help='verbose output',
            action='count', default=0)

    # ----------------------------------------------------------------------------------------------
    def add_timecode_arguments(self) -> _ArgumentGroup:
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
        group.add_argument('--start',
            help='starting source position',
            action='store')
        group.add_argument('--duration',
            help='duration to encode',
            action='store')
        group.add_argument('--end',
            help='ending source position',
            action='store')
        group.add_argument('--segment',
            help='segment start and end source position; may be specified multiple times to encode '
                'multiple segments to separate files; enables --always-number when specified more '
                'than once',
            nargs=2, metavar=('START', 'END'), action='append', dest='segments')
        return group

    # ----------------------------------------------------------------------------------------------
    def add_audio_filter_arguments(self) -> _ArgumentGroup:
        """
        Add a new group containing filter arguments that apply to audio-only encodes and return the
        group.
        """
        group = self.add_argument_group('filter arguments')
        group.add_argument('--fade-in',
            help='apply an audio fade-in at the start of each output',
            action='store', type=float, metavar='SECONDS')
        group.add_argument('--fade-out',
            help='apply an audio fade-out at the end of each output',
            action='store', type=float, metavar='SECONDS')
        group.add_argument('-f', '--filter',
            help='custom audio filter, passed as -af argument to ffmpeg',
            action='append', dest='audio_filter')
        group.add_argument('--volume',
            help='amplitude (volume) multiplier, < 1.0 to reduce volume, or > 1.0 to increase '
                'volume; recommended to use replaygain to tag the file post-conversion, instead',
            action='store', type=float, default=1.0)
        return group

    # ----------------------------------------------------------------------------------------------
    def add_channel_layout_fix_argument(self) -> None:
        """
        Add a channel layout fix argument.
        """
        self.add_argument('--channel-layout-fix',
            help='apply a channel layout fix to 4.1, 5.0, 5.1(side) audio sources to output a '
                'compatible 5.1(rear) layout; may be a colon-delimited list to apply the fix to '
                'multiple audio tracks from the source; choices are 4.1, 5.0, 5.1; 0 or blank '
                'apply no fix',
            action=DelimitedValueAction, metavar="FIX_STRING",
            value_choices=['0', '4.1', '5.0', '5.1'], default=['0'])

    # ----------------------------------------------------------------------------------------------
    def add_source_file_arguments(self, help: str | None=None) -> None:
        """
        Add a positional argument that requires one or more source files.
        """
        self.add_argument('source_files',
            help='source files to convert' if help is None else help,
            action='store', metavar='source_file', nargs='+')

    # ----------------------------------------------------------------------------------------------
    def add_passthrough_arguments(self) -> _ArgumentGroup:
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
                ('segments' in args and args.segment is not None)):
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
        if 'source_files' in parsed and parsed.source_files is not None:
            self._check_source_files_exist(parsed.source_files)
        return parsed
