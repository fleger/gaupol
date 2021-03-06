# -*- coding: utf-8 -*-

# Copyright (C) 2006-2010 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Gaupol is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Gaupol. If not, see <http://www.gnu.org/licenses/>.

"""TMPlayer file."""

import aeidon
import re

__all__ = ("TMPlayer",)


class TMPlayer(aeidon.SubtitleFile):

    """TMPlayer file."""

    _re_one_digit_hour = re.compile(r"^-?\d:\d\d:\d\d:")
    _re_two_digit_hour = re.compile(r"^-?\d\d:\d\d:\d\d:")
    format = aeidon.formats.TMPLAYER
    mode = aeidon.modes.TIME

    def __init__(self, path, encoding, newline=None):
        """Initialize an :class:`MPsub` object."""
        aeidon.SubtitleFile.__init__(self, path, encoding, newline)
        self.two_digit_hour = True

    def copy_from(self, other):
        """Copy generic properties from `other` file."""
        aeidon.SubtitleFile.copy_from(self, other)
        if self.format == other.format:
            self.two_digit_hour = other.two_digit_hour

    def read(self):
        """
        Read file and return subtitles.

        Raise :exc:`IOError` if reading fails.
        Raise :exc:`UnicodeError` if decoding fails.
        """
        subtitles = [self._get_subtitle()]
        for line in self._read_lines():
            match = self._re_one_digit_hour.search(line)
            if match is not None:
                i = match.span()[1]
                subtitle = self._get_subtitle()
                subtitle.start_time = ("-0" + line[1:i - 1] + ".000"
                                       if line.startswith("-") else
                                       "0" + line[:i - 1] + ".000")

                subtitles[-1].end_time = subtitle.start_time
                subtitle.main_text = line[i:].replace("|", "\n")
                subtitles.append(subtitle)
                self.two_digit_hour = False
            match = self._re_two_digit_hour.search(line)
            if match is not None:
                i = match.span()[1]
                subtitle = self._get_subtitle()
                subtitle.start_time = line[:i - 1] + ".000"
                subtitles[-1].end_time = subtitle.start_time
                subtitle.main_text = line[i:].replace("|", "\n")
                subtitles.append(subtitle)
                self.two_digit_hour = True
        subtitles.pop(0)
        subtitles[-1].duration_seconds = 5
        return subtitles

    def write_to_file(self, subtitles, doc, fobj):
        """
        Write `subtitles` from `doc` to `fobj`.

        Raise :exc:`IOError` if writing fails.
        Raise :exc:`UnicodeError` if encoding fails.
        """
        for subtitle in subtitles:
            start = subtitle.calc.round(subtitle.start_time, 0)
            fobj.write("{}:".format(start[:-4] if self.two_digit_hour
                                    else ("-" + start[2:-4]
                                          if start.startswith("-")
                                          else start[1:-4])))

            fobj.write(subtitle.get_text(doc).replace("\n", "|"))
            fobj.write(self.newline.value)
