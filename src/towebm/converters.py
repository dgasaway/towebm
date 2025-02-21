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
import collections.abc
from datetime import datetime
import os
import re
import subprocess
from typing import TYPE_CHECKING, NamedTuple
if TYPE_CHECKING:
    from argparse import Namespace

from towebm.formats import AudioFormat, VideoFormat, AudioQualityType
from towebm import argparsers

# --------------------------------------------------------------------------------------------------
class Segment(NamedTuple):
    """
    Represents a segment of the input file bound by ffmpeg duration strings.
    """
    start: str | None
    end: str | None
    duration: str | None

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
    def duration_to_seconds(self, duration: str) -> float | None:
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

    # ----------------------------------------------------------------------------------------------
    def get_audio_filters(self, segment: Segment) -> list[str]:
        """
        Return a list of audio filters, one element per standard filter or audio filter arg.
        """
        filters: list[str] = []

        # Want to apply standard filters is a certain order, so do not loop.
        if self.args.volume != 1.0:
            filters.append(f'volume={self.args.volume}')

        # The fade filters take a start time relative to the start of the output, rather than the
        # start of the source.  So, fade in will start at 0 secs.  Fade out needs to get the output
        # duration and subtract the fade out duration.
        f_in = self.args.fade_in
        f_out = self.args.fade_out
        if f_in is not None:
            filters.append(f'afade=t=in:st=0:d={f_in}')
        if f_out is not None:
            if segment.duration is not None:
                duration = self.duration_to_seconds(segment.duration)
            else:
                start = 0.0 if segment.start is None else self.duration_to_seconds(segment.start)
                duration = self.duration_to_seconds(segment.end) - start
            filters.append(f'afade=t=out:st={duration - f_out}:d={f_out}')

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
        if segment.start is not None:
            result += ['-accurate_seek', '-ss', segment.start]
        if segment.end is not None:
            result += ['-to', segment.end]
        if segment.duration is not None:
            result += ['-t', segment.duration]
        return result

    # ----------------------------------------------------------------------------------------------
    def get_base_segment_args(self, segment: Segment, file_name: str) -> list[str]:
        """
        Return a list of ffmpeg arguments for transcoding the specified segment of the specified
        file.
        """
        result = ['ffmpeg', '-nostdin', '-hide_banner']
        result += self.get_segment_arguments(segment)
        result += [ '-i', file_name ]
        return result

    # ----------------------------------------------------------------------------------------------
    def get_audio_quality_arg(self, quality: float, stream_index: int | None=None) -> list[str]:
        """
        Return a list of ffmpeg arguments for a specified audio quality and optional output stream
        index.
        """
        quality_sfx = ''
        if self.audio_format.quality_type == AudioQualityType.QUALITY:
            arg = '-q:a'
        elif self.audio_format.quality_type == AudioQualityType.COMP_LEVEL:
            arg = '-compression_level:a'
        else:
            arg = '-b:a'
            quality_sfx = 'k'

        arg = arg if stream_index is None else f'{arg}:{stream_index}'
        return [arg, f'{quality}{quality_sfx}']

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

    # ----------------------------------------------------------------------------------------------
    def get_audio_metadata_map_args(self) -> list[str]:
        """
        Return a list of ffmpeg arguments to copy audio metadata from the input streams to the
        matching output streams.
        """
        result: list[str] = []
        if isinstance(self.args.audio_quality, collections.abc.Sequence):
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
    def process_segment(self, segment: Segment, file_name: str) -> None:
        """
        Execute the requested action for a single output file.
        """

    # ----------------------------------------------------------------------------------------------
    def process_file(self, file_name: str) -> None:
        """
        Executes the requested action for a single input file.
        """
        if self.args.segments is not None:
            for segment in self.args.segments:
                self.process_segment(Segment(segment[0], segment[1], None), file_name)
        else:
            segment = Segment(self.args.start, self.args.end, self.args.duration)
            self.process_segment(segment, file_name)

    # ----------------------------------------------------------------------------------------------
    def main(self, args: list[str] | None=None) -> int:
        """
        Execute the operations indicated by specified argument strings.
        """
        self.args = self.parse_args(args)
        if self.args.verbose >= 1:
            print (self.args)

        # We'll treat each input file as it's own job, and continue to the next if there is a
        # problem.
        rc = 0
        for source_file in self.args.source_files:
            try:
                self.process_file(source_file)
            except subprocess.CalledProcessError as ex:
                if rc == 0 or ex.returncode > rc:
                    rc = ex.returncode
                print('Execution error, proceeding to next source file.')

        return rc

    # --------------------------------------------------------------------------------------------------
    def execute_command(self, command: list[str]) -> None:
        """
        Execute the specified command and arguments.
        """
        if self.args.pretend or self.args.verbose >= 1:
            print(command)
        if not self.args.pretend:
            subprocess.check_call(command)

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
        return argparsers.AudioConverterArgumentParser(self.audio_format).parse_args(args)

    # ----------------------------------------------------------------------------------------------
    def get_ffmpeg_command(self, segment: Segment, file_name: str) -> list[str]:
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
        result += self.get_audio_metadata_map_args()
        result += self.args.passthrough_args

        safe_file_name = self.get_safe_filename(f'{title}.{self.audio_format.container}')
        result.append(safe_file_name)

        return result

    # ----------------------------------------------------------------------------------------------
    def process_segment(self, segment: Segment, file_name: str) -> None:
        """
        Execute the requested action for a single output file.
        """
        cmd = self.get_ffmpeg_command(segment, file_name)
        if self.args.pretend or self.args.verbose >= 1:
            print(cmd)
        if not self.args.pretend:
            subprocess.check_call(cmd)

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
        return argparsers.VideoConverterArgumentParser(self.video_format).parse_args(args)

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

        # The fade filters take a start time relative to the start of the output, rather than the
        # start of the source.  So, fade in will start at 0 secs.  Fade out needs to get the output
        # duration and subtract the fade out duration.
        if self.args.fade_in is not None:
            filters.append(f'fade=t=in:st=0:d={self.args.fade_in}')
        if self.args.fade_out is not None:
            if segment.duration is not None:
                duration = self.duration_to_seconds(segment.duration)
            else:
                start = 0.0 if segment.start is None else self.duration_to_seconds(segment.start)
                duration = self.duration_to_seconds(segment.end) - start
            filters.append(f'fade=t=out:st={duration - self.args.fade_out}:d={self.args.fade_out}')

        if self.args.video_filter is not None:
            filters += self.args.video_filter

        if len(filters) == 0:
            filters = ['copy']

        return ['-filter_complex', '[0:v]' + ','.join(filters)]

    # --------------------------------------------------------------------------------------------------
    def get_audio_codec_args(self, segment: Segment):
        """
        Return a list of ffmpeg arguments for the audio portion of a single output file.
        """
        if len([q for q in self.args.audio_quality if q is not None and q > 0]) > 0:
            result = ['-c:a', self.video_format.audio_format.ffmpeg_codec]
            result += self.get_audio_filter_args(segment)
            result += self.get_audio_quality_args()
        else:
            result = ['-an']

        return result

    # --------------------------------------------------------------------------------------------------
    def get_video_codec_args(self, segment: Segment, pass_args: list[str]):
        """
        Return a list of ffmpeg arguments for the audio portion of a single output file.
        """
        result = [
            '-c:v', self.video_format.ffmpeg_codec,
            self.video_format.video_quality_arg, str(self.args.quality),
            '-b:v', '0',
        ]
        result += self.video_format.codec_args
        result += pass_args
        result += self.get_video_filter_args(segment)

        return result

    # --------------------------------------------------------------------------------------------------
    def get_one_pass_command(self, segment: Segment, file_name: str) -> list[str]:
        """
        Return a list of arguments to run ffmpeg for a one-pass trancode of a single output file.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]

        result = self.get_base_segment_args(segment, file_name)
        result += self.get_video_codec_args(segment, self.video_format.pass1_codec_args)
        result += self.get_audio_codec_args(segment)
        result += [
            '-f', self.video_format.ffmpeg_output,
            '-metadata', f'title={title}'
        ]
        result += self.get_audio_metadata_map_args()
        result += self.args.passthrough_args

        container = (
            self.args.container if 'container' in self.args else
            self.video_format.container_options[0])

        safe_file_name = self.get_safe_filename(f'{title}.{container}')
        result.append(safe_file_name)

        return result

    # --------------------------------------------------------------------------------------------------
    def get_pass1_command(self, segment: Segment, file_name: str) -> list[str]:
        """
        Return a list of arguments to run ffmpeg for pass one of a single output file.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]

        result = self.get_base_segment_args(segment, file_name)
        result += self.get_video_codec_args(segment, self.video_format.pass1_codec_args)
        result += [
            # No audio.
            '-an',
            # This is still required even if no output.
            '-f', self.video_format.ffmpeg_output,
            # Always overwrite an existing log file.
            '-y',
            '-pass', '1',
            '-passlogfile', title,
        ]
        result += self.args.passthrough_args
        result.append('/dev/null')

        return result

    # --------------------------------------------------------------------------------------------------
    def get_pass2_command(self, segment: Segment, file_name: str) -> list[str]:
        """
        Return a list of arguments to run ffmpeg for pass two of a single output file.
        """
        title = os.path.splitext(os.path.basename(file_name))[0]

        result = self.get_base_segment_args(segment, file_name)
        result += self.get_video_codec_args(segment, self.video_format.pass2_codec_args)
        result += self.get_audio_codec_args(segment)
        result += [
            '-f', self.video_format.ffmpeg_output,
            '-pass', '2',
            '-passlogfile', title,
            '-metadata', f'title={title}'
        ]
        result += self.get_audio_metadata_map_args()
        result += self.args.passthrough_args

        unsafe_file_name = f'{title}.{self.args.container}'
        safe_file_name = self.get_safe_filename(unsafe_file_name)
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
            return ['mv',
                    f'{title}-0.log',
                    f'{title}_{datetime.now():%Y%m%d-%H%M%S}.log']

    # --------------------------------------------------------------------------------------------------
    def process_segment(self, segment: Segment, file_name: str) -> None:
        """
        Execute the requested action for a single output file.
        """
        if len(self.video_format.passes) == 1:
            self.execute_command(self.get_one_pass_command(segment, file_name))
            return
        
        if 'only_pass' not in self.args or self.args.only_pass is None:
            passes = self.video_format.passes
        else:
            passes = [ int(self.args.only_pass) ]
        if 1 in passes:
            self.execute_command(self.get_pass1_command(segment, file_name))
        if 2 in passes:
            self.execute_command(self.get_pass2_command(segment, file_name))
            self.execute_command(self.get_log_command(file_name))
