# converters.py - Shared routines.
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

from abc import ABC, abstractmethod
from datetime import datetime
import os
import subprocess
import sys

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from argparse import Namespace
    from towebm.formats import AudioFormat, VideoFormat
    from towebm.argparsers import Segment

from towebm.argparsers import AudioConverterArgumentParser, VideoConverterArgumentParser

# --------------------------------------------------------------------------------------------------
class Converter(ABC):
    """
    A base class that converts source audio/video source files to audio or video output files based
    on a list of argument strings provided to main().
    """
    def __init__(self, audio_format: AudioFormat):
        self.args: Namespace = None
        self.audio_format = audio_format

    # ----------------------------------------------------------------------------------------------
    @abstractmethod
    def parse_args(self, args: list[str] | None=None) -> Namespace:
        """
        Convert the specified argument strings, or sys.argv if None, to a namespace.  Return the
        populated namespace.
        """

    # ----------------------------------------------------------------------------------------------
    def get_safe_filename(self, filename: str) -> str:
        """
        Return the source file name if no file exists with the given name and the `always_number`
        arg is false; return the source file name with an understore and two-digit sequence number
        appended to make the file name unique if the source file name is not unique or the
        `always_number` arg is true; if no such file name is unique, return the source file name.
        """
        if not self.args.always_number and not os.path.exists(filename):
            return filename
        else:
            (base, ext) = os.path.splitext(filename)
            for i in range(100):
                s = f'{base}_{i:02}{ext}'
                if not os.path.exists(s):
                    return s
            return filename

    # ----------------------------------------------------------------------------------------------
    def get_fade_filters(self, segment: Segment, filter_name: str) -> list[str]:
        """
        Return a list of fade-in and/or fade-filters for the specified arguments based on fade
        argments, or an empty list if none were specified in the arguments.
        """
        # The fade filters take a start time relative to the start of the output, rather than the
        # start of the source.  So, fade in will start at 0 secs.  Fade out needs to get the output
        # duration and subtract the fade out duration.
        filters = []
        if self.args.fade_in is not None:
            filters.append(f'{filter_name}=t=in:st=0:d={self.args.fade_in}')
        if self.args.fade_out is not None and segment.duration is not None:
            start = segment.duration - self.args.fade_out
            filters.append(f'{filter_name}=t=out:st={start}:d={self.args.fade_out}')
        return filters

    # ----------------------------------------------------------------------------------------------
    def get_audio_filters(self, segment: Segment) -> list[str]:
        """
        Return a list of audio filters, one element per standard filter or audio filter arg.
        """
        filters: list[str] = []

        # Want to apply standard filters is a certain order, so do not loop.
        if self.args.volume != 1.0:
            filters.append(f'volume={self.args.volume}')
        filters += self.get_fade_filters(segment, 'afade')
        if self.args.audio_filter is not None:
            filters += self.args.audio_filter

        return filters

    # ----------------------------------------------------------------------------------------------
    def get_audio_filter_args(self, segment: Segment) -> list[str]:
        """
        Return a list of ffmpeg arguments that apply all of the selected audio filters specified
        in the args, or an empty list if none apply.
        """
        filters = self.get_audio_filters(segment)
        per_track_filters = []

        # We need to specify the input index for each that audio stream that will be output.  So, we
        # iterate the list with index, rather than use list comprehension.
        for i, quality in enumerate(self.args.audio_quality):
            if quality is not None and quality > 0:
                # channel_layout_fix is going to use the same index, but it may have fewer values
                # specified than audio_quality.
                map_fix = (
                    'channel_layout_fix' in self.args and
                    i < len(self.args.channel_layout_fix) and
                    self.args.channel_layout_fix[i] is not None and
                    self.args.channel_layout_fix[i] != '0')
                if map_fix:
                    layout = self.args.channel_layout_fix[i]
                    if layout == '5.1':
                        flts = ['channelmap=channel_layout=5.1']
                    elif layout == '5.0':
                        flts = ['pan=5.1|FR=FR|FL=FL|FC=FC|BL=SL|BR=SR']
                    elif layout == '4.1':
                        flts = ['pan=5.1|FR=FR|FL=FL|FC=FC|BL=BC|BR=BC|LFE=LFE']
                    else:
                        msg = f'unexpected channel layout fix value {layout}'
                        raise ValueError(msg)
                    flts += filters
                elif len(filters) == 0:
                    flts = ['acopy']
                else:
                    flts = filters
                per_track_filters.append(f'[0:a:{i}]' + ','.join(flts))

        if len(per_track_filters) == 0:
            return []
        else:
            return ['-filter_complex', ';'.join(per_track_filters)]

    # ----------------------------------------------------------------------------------------------
    def get_segment_arguments(self, segment: Segment) -> list[str]:
        """
        Return a list of ffmepg arguments to select the specified source segment, or an empty list
        if no segment was specified.
        """
        result = []
        # For the args, it's best to use the original ffmpeg strings.
        if segment.start_str is not None:
            result += ['-accurate_seek', '-ss', segment.start_str]
        if segment.end_str is not None:
            result += ['-to', segment.end_str]
        if segment.duration_str is not None:
            result += ['-t', segment.duration_str]
        return result

    # ----------------------------------------------------------------------------------------------
    def get_base_segment_args(self, segment: Segment, file_name: str) -> list[str]:
        """
        Return a list of ffmpeg arguments for transcoding the specified segment of the specified
        file.
        """
        result = ['ffmpeg', '-nostdin', '-hide_banner']
        result += self.get_segment_arguments(segment)
        result += ['-i', file_name]
        result += ['-f', self.args.container.ffmpeg_format]
        return result

    # ----------------------------------------------------------------------------------------------
    def get_audio_quality_arg(self, quality: float, stream_index: int | None=None) -> list[str]:
        """
        Return a list of ffmpeg arguments for a specified audio quality and optional output stream
        index.
        """
        quality_arg = self.audio_format.quality_arg
        arg = f'{quality_arg.ffmpeg_arg}:a'
        if stream_index is not None:
            arg += f':{stream_index}'

        value = str(quality)
        if quality_arg.ffmpeg_value_suffix is not None:
            value += quality_arg.ffmpeg_value_suffix

        return [arg, value]

    # ----------------------------------------------------------------------------------------------
    def get_audio_quality_args(self) -> list[str]:
        """
        Return a list of one or more sets of ffmpeg audio quality arguments based on the audio
        quality arguments in the args.
        """
        # We only output a quality for non-zero values, and since the stream index is the output
        # index, we can use the index of a filtered list.
        result = []
        qualities = [q for q in self.args.audio_quality if q is not None and q > 0]
        for i, quality in enumerate(qualities):
            result += self.get_audio_quality_arg(quality, i)
        return result

    # ----------------------------------------------------------------------------------------------
    def get_audio_metadata_map_arg(self,
        output_index: int=0, input_index: int | None=None) -> list[str]:
        """
        Return a list two ffmpeg arguments for copying audio stream metadata from a specified
        source index to a specified output stream index.
        """
        arg = f'-map_metadata:s:a:{output_index}'
        if input_index is None:
            return [arg, '0:s:a']
        else:
            return [arg, f'0:s:a:{input_index}']

    # --------------------------------------------------------------------------------------------------
    def get_audio_format_args(self) -> list[str]:
        """
        Return a list of the ffmpeg audio codec arguments from the audio format specification.
        """
        codec_args = self.audio_format.codec_args
        if codec_args is not None and len(codec_args) > 0:
            return codec_args
        else:
            return []

    # ----------------------------------------------------------------------------------------------
    def is_iterable(self, obj) -> bool:
        """
        Determine whether the specified object is iterable.
        """
        try:
            iter(obj)
        except TypeError:
            return False
        else:
            return True

    # ----------------------------------------------------------------------------------------------
    def get_audio_metadata_map_args(self) -> list[str]:
        """
        Return a list of ffmpeg arguments to copy audio metadata from the input streams to the
        matching output streams.
        """
        result: list[str] = []
        if self.is_iterable(self.args.audio_quality):
            # We need both the input and output index to create the map.
            output_index = 0
            for input_index, quality in enumerate(self.args.audio_quality):
                if quality is not None and quality > 0:
                    result += self.get_audio_metadata_map_arg(output_index, input_index)
                    output_index += 1
        elif self.args.audio_quality > 0:
            result = self.get_audio_metadata_map_arg()
        return result

    # ----------------------------------------------------------------------------------------------
    @abstractmethod
    def get_segment_commands(self, segment: Segment, file_name: str) -> list[list[str]]:
        """
        Return the list of commands to transcode the specified segment of the specified input file.
        """

    # ----------------------------------------------------------------------------------------------
    def process_segment(self, segment: Segment, file_name: str) -> None:
        """
        Execute the requested action for a single output file.
        """
        commands = self.get_segment_commands(segment, file_name)
        if self.args.pretend or self.args.verbose >= 1:
            for command in commands:
                #print(' '.join(command))
                print(command)
                print()
        if not self.args.pretend:
            for command in commands:
                subprocess.check_call(command)

    # ----------------------------------------------------------------------------------------------
    def process_file(self, file_name: str) -> None:
        """
        Executes the requested action for a single input file.
        """
        for segment in self.args.all_segments:
            self.process_segment(segment, file_name)

    # ----------------------------------------------------------------------------------------------
    def setup(self, args: list[str] | None=None) -> int:
        """
        Convert the specified argument strings, or sys.argv if None, to a namespace and assign then
        to `self.args`.  If `self.args` is set, issues a warning.
        """
        if args is not None:
            print('WARNING: overriding args', file=sys.srderr)
        self.args = self.parse_args(args)
        if self.args.verbose >= 2:
            print (self.args)

    # ----------------------------------------------------------------------------------------------
    def main(self, args: list[str] | None=None) -> int:
        """
        Execute the operations indicated by specified argument strings, or sys.argv if None.
        """
        # We'll treat each input file as it's own job, and continue to the next if there is a
        # problem.
        self.setup(args)
        rc = 0
        for source_file in self.args.source_files:
            try:
                self.process_file(source_file)
            except subprocess.CalledProcessError as ex:
                if rc == 0 or ex.returncode > rc:
                    rc = ex.returncode
                print('Execution error, proceeding to next source file.', file=sys.stderr)

        return rc

# --------------------------------------------------------------------------------------------------
class AudioConverter(Converter):
    """
    An audio converter.
    """
    # ----------------------------------------------------------------------------------------------
    def __init__(self, audio_format: AudioFormat):
        super().__init__(audio_format)

    # ----------------------------------------------------------------------------------------------
    def parse_args(self, args: list[str] | None=None) -> Namespace:
        """
        Convert the specified argument strings, or sys.argv if None, to a namespace.  Return the
        populated namespace.
        """
        return AudioConverterArgumentParser(self.audio_format).parse_args(args)

    # ----------------------------------------------------------------------------------------------
    def get_segment_command(self, segment: Segment, file_name: str) -> list[str]:
        """
        Return the arguments to run ffmpeg for a single output file.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]

        result = self.get_base_segment_args(segment, file_name)
        result += [
            '-vn',
            '-c:a', self.audio_format.ffmpeg_codec
        ]
        result += self.get_audio_filter_args(segment)
        result += self.get_audio_quality_args()
        result += self.get_audio_format_args()
        result += self.get_audio_metadata_map_args()
        result += self.args.passthrough_args

        safe_file_name = self.get_safe_filename(f'{title}{self.args.container.extension}')
        result.append(safe_file_name)

        return result

    # ----------------------------------------------------------------------------------------------
    def get_segment_commands(self, segment: Segment, file_name: str) -> list[list[str]]:
        """
        Return the list of commands to transcode the specified segment of the specified input file.
        """
        return [self.get_segment_command(segment, file_name)]

# --------------------------------------------------------------------------------------------------
class VideoConverter(Converter):
    """
    """
    # ----------------------------------------------------------------------------------------------
    def __init__(self, video_format: VideoFormat):
        super().__init__(video_format.audio_format)
        self.video_format = video_format

    # ----------------------------------------------------------------------------------------------
    def parse_args(self, args: list[str] | None=None) -> Namespace:
        """
        Convert the specified argument strings, or sys.argv if None, to a namespace.  Return the
        populated namespace.
        """
        return VideoConverterArgumentParser(self.video_format).parse_args(args)

    # ----------------------------------------------------------------------------------------------
    def get_video_filter_args(self, segment: Segment) -> list[str]:
        """
        Return a list of ffmpeg arguments that apply all of the selected video filters requested in
        the specified script arguments, or an empty list if none apply.
        """
        filters: list[str] = []

        # Deinterlace first.
        parity = ''
        if self.args.parity is not None:
            parity = ':' + self.args.parity
        if self.args.deinterlace == 'frame':
            filters.append('bwdif=send_frame' + parity)
        elif self.args.deinterlace == 'field':
            filters.append('bwdif=send_field' + parity)
        elif self.args.deinterlace == 'ivtc':
            filters += ['fieldmatch', 'decimate']
        elif self.args.deinterlace == 'ivtc+':
            filters += ['fieldmatch', 'bwdif=send_frame', 'decimate']
        elif self.args.deinterlace == 'selframe':
            filters += ['fieldmatch', 'bwdif=0:-1:1']

        # Want to apply standard filters is a certain order, so do not loop.
        if self.args.standard_filter is not None:
            if 'gray' in self.args.standard_filter:
                filters.append('format=gray')
            if 'crop43' in self.args.standard_filter:
                filters.append('crop=w=(in_h*4/3)')

        if self.args.gamma != 1.0:
            filters.append(f'eq=gamma={self.args.gamma}')

        if self.args.crop_width is not None or self.args.crop_height is not None:
            if self.args.crop_width is not None and self.args.crop_height is not None:
                crop = 'crop=x={x[0]}:w=in_w-{x[0]}-{x[1]}:y={y[0]}:h=in_h-{y[0]}-{y[1]}'
            elif self.args.crop_width is not None:
                crop = 'crop=x={x[0]}:w=in_w-{x[0]}-{x[1]}'
            else:
                crop = 'crop=y={y[0]}:h=in_h-{y[0]}-{y[1]}'
            filters.append(crop.format(x=self.args.crop_width, y=self.args.crop_height))

        if self.args.standard_filter is not None:
            if 'scale23' in self.args.standard_filter:
                filters.append('scale=h=in_h*2/3:w=-1')

        filters += self.get_fade_filters(segment, 'fade')

        if self.args.video_filter is not None:
            filters += self.args.video_filter

        if len(filters) == 0:
            filters = ['copy']

        return ['-filter_complex', '[0:v]' + ','.join(filters)]

    # --------------------------------------------------------------------------------------------------
    def get_audio_codec_args(self, segment: Segment) -> list[str]:
        """
        Return a list of ffmpeg audio codec and audio filter arguments for the specified segment.
        """
        if len([q for q in self.args.audio_quality if q is not None and q > 0]) > 0:
            result = ['-c:a', self.video_format.audio_format.ffmpeg_codec]
            result += self.get_audio_filter_args(segment)
            result += self.get_audio_format_args()
            result += self.get_audio_quality_args()
        else:
            result = ['-an']

        return result

    # --------------------------------------------------------------------------------------------------
    def get_video_format_args(self, pass_num: int) -> list[str]:
        """
        Return a list of the ffmpeg video codec arguments from the video format specification for the
        specified pass.
        """
        codec_args = self.video_format.codec_args
        result = []
        if codec_args is not None and len(codec_args) > 0:
            if codec_args[0] is not None:
                result.extend(codec_args[0])
            if len(codec_args) > pass_num and codec_args[pass_num] is not None:
                result.extend(codec_args[pass_num])
        for mapped_arg in self.video_format.mapped_codec_args:
            result.append(mapped_arg.ffmpeg_arg)
            result.append(str(getattr(self.args, mapped_arg.dest)))

        return result

    # --------------------------------------------------------------------------------------------------
    def get_video_codec_args(self, segment: Segment, pass_num: int) -> list[str]:
        """
        Return a list of ffmpeg video codec and video filter arguments for the specified segment and
        pass number.
        """
        result = [
            '-c:v', self.video_format.ffmpeg_codec,
            #self.video_format.video_quality_arg, str(self.args.quality)
        ]
        result += self.get_video_format_args(pass_num)
        result += self.get_video_filter_args(segment)

        return result

    # --------------------------------------------------------------------------------------------------
    def get_one_pass_command(self, segment: Segment, file_name: str) -> list[str]:
        """
        Return a complete ffmpeg command and arguments to perform a one-pass transcode of the specified
        segment and input file.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]

        result = self.get_base_segment_args(segment, file_name)
        result += self.get_video_codec_args(segment, 1)
        result += self.get_audio_codec_args(segment)
        result += ['-metadata', f'title={title}']
        result += self.get_audio_metadata_map_args()
        result += self.args.passthrough_args

        safe_file_name = self.get_safe_filename(f'{title}{self.args.container.extension}')
        result.append(safe_file_name)

        return result

    # --------------------------------------------------------------------------------------------------
    def get_not_last_pass_command(self, segment: Segment, file_name: str, pass_num: int) -> list[str]:
        """
        Return a complete ffmpeg command and arguments to perform the specified video-only no-output
        pass for the specified segment and input file.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]

        result = self.get_base_segment_args(segment, file_name)
        result += self.get_video_codec_args(segment, pass_num)
        result += [
            # No audio.
            '-an',
            # Always overwrite an existing log file.
            '-y',
            '-pass', str(pass_num),
            '-passlogfile', title,
        ]
        result += self.args.passthrough_args
        result.append('/dev/null')

        return result

    # --------------------------------------------------------------------------------------------------
    def get_last_pass_command(self, segment: Segment, file_name: str, pass_num: int) -> list[str]:
        """
        Return a complete ffmpeg command and arguments to perform the last pass for the specified
        segment and input file.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]

        result = self.get_base_segment_args(segment, file_name)
        result += self.get_video_codec_args(segment, pass_num)
        result += self.get_audio_codec_args(segment)
        result += [
            '-pass', str(pass_num),
            '-passlogfile', title,
            '-metadata', f'title={title}'
        ]
        result += self.get_audio_metadata_map_args()
        result += self.args.passthrough_args

        safe_file_name = self.get_safe_filename(f'{title}{self.args.container.extension}')
        result.append(safe_file_name)

        return result

    # --------------------------------------------------------------------------------------------------
    def get_log_command(self, file_name: str) -> list[str]:
        """
        Return a list of arguments to either delete or rename the pass one log file, as requested by the
        user in the script arguemnts.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]
        if self.args.delete_log:
            return ['rm', f'{title}-0.log']
        else:
            return ['mv', f'{title}-0.log', f'{title}_{datetime.now():%Y%m%d-%H%M%S}.log']

    # --------------------------------------------------------------------------------------------------
    def get_segment_commands(self, segment: Segment, file_name: str) -> None:
        """
        Return the list of commands to transcode the specified segment of the specified input file.
        """
        if self.video_format.passes == 1:
            return [self.get_one_pass_command(segment, file_name)]

        if 'pass_num' not in self.args or self.args.pass_num is None:
            passes = range(1, self.video_format.passes + 1)
        else:
            passes = [ int(self.args.pass_num) ]

        commands = []
        for pass_num in passes:
            if pass_num < self.video_format.passes:
                commands.append(self.get_not_last_pass_command(segment, file_name, pass_num))
            else:
                commands.append(self.get_last_pass_command(segment, file_name, pass_num))
                commands.append(self.get_log_command(file_name))

        return commands
