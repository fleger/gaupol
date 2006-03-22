# Copyright (C) 2005 Osmo Salomaa
#
# This file is part of Gaupol.
#
# Gaupol is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Gaupol is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gaupol; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""String and regular expression finder and replacer."""


try:
    from psyco.classes import *
except ImportError:
    pass

import re


class Finder(object):

    """String and regular expression finder and replacer."""

    def __init__(self):

        self.is_regex    = False
        self.match_span  = None
        self.pattern     = None
        self.position    = 0
        self.regex       = None
        self.replacement = None
        self.text        = None

    def next(self):
        """
        Get next match of pattern.

        Raise StopIteration if no next match found.
        Return two-tuple: match start position, match end position.
        """
        if self.is_regex:
            match = self.regex.search(self.text, self.position)
            if not match:
                raise StopIteration
            self.match_span = match.span()
        else:
            try:
                index = self.text.index(self.pattern, self.position)
            except ValueError:
                raise StopIteration
            self.match_span = (index, index + len(self.pattern))

        self.position = self.match_span[1]
        return self.match_span

    def previous(self):
        """
        Get previous match of pattern.

        Raise StopIteration if no previous match found.
        Return two-tuple: match start position, match end position.
        """
        if self.is_regex:
            iterator = self.regex.finditer(self.text)
            match = None
            while True:
                try:
                    candidate_match = iterator.next()
                    if candidate_match.end() <= self.position:
                        match = candidate_match
                    else:
                        break
                except StopIteration:
                    break
            if match is None:
                raise StopIteration
            self.match_span = match.span()
        else:
            try:
                index = self.text.rindex(self.pattern, 0, self.position)
            except ValueError:
                raise StopIteration
            self.match_span = (index, index + len(self.pattern))

        self.position = self.match_span[0]
        return self.match_span

    def replace(self):
        """Replace current match."""

        start = self.match_span[0]
        end   = self.match_span[1]

        if self.is_regex:
            text_body = self.text[start:]
            text_body = self.regex.sub(self.replacement, text_body, 1)
            self.text = self.text[:start] + text_body
        else:
            self.text = self.text[:start] + self.replacement + self.text[end:]

    def replace_all(self):
        """
        Replace all occurences of pattern.

        Return amount of substitutions made.
        """
        if self.is_regex:
            self.text, count = self.regex.subn(self.replacement, self.text)
        else:
            count = self.text.count(self.pattern)
            self.text = self.text.replace(self.pattern, self.replacement)

        return count

    def set_regex(self, pattern, flags=0):
        """Set and use regular expression."""

        self.is_regex = True
        self.pattern = pattern
        self.regex = re.compile(pattern, flags|re.UNICODE)


if __name__ == '__main__':

    from gaupol.test import Test

    class TestFinder(Test):

        def get_finder(self):

            finder = Finder()
            finder.text = \
                'One only risks it, because\n' \
                'one\'s survival depends on it.'

            return finder

        def test_next(self):

            finder = self.get_finder()
            finder.pattern = 'it'
            assert finder.next() == (15, 17)
            assert finder.match_span == (15, 17)
            assert finder.position == 17
            assert finder.next() == (53, 55)
            assert finder.match_span == (53, 55)
            assert finder.position == 55
            try:
                finder.next()
                raise AssertionError
            except StopIteration:
                pass

            finder = self.get_finder()
            finder.set_regex(r'\bit\b', re.MULTILINE)
            assert finder.next() == (15, 17)
            assert finder.match_span == (15, 17)
            assert finder.position == 17
            assert finder.next() == (53, 55)
            assert finder.match_span == (53, 55)
            assert finder.position == 55
            try:
                finder.next()
                raise AssertionError
            except StopIteration:
                pass

        def test_previous(self):

            finder = self.get_finder()
            finder.pattern = 'it'
            finder.position = len(finder.text)
            assert finder.previous() == (53, 55)
            assert finder.match_span == (53, 55)
            assert finder.position == 53
            assert finder.previous() == (15, 17)
            assert finder.match_span == (15, 17)
            assert finder.position == 15
            try:
                finder.previous()
                raise AssertionError
            except StopIteration:
                pass

            finder = self.get_finder()
            finder.set_regex(r'\bit\b', re.MULTILINE)
            finder.position = len(finder.text)
            assert finder.previous() == (53, 55)
            assert finder.match_span == (53, 55)
            assert finder.position == 53
            assert finder.previous() == (15, 17)
            assert finder.match_span == (15, 17)
            assert finder.position == 15
            try:
                finder.previous()
                raise AssertionError
            except StopIteration:
                pass

        def test_replace(self):

            finder = self.get_finder()
            finder.pattern = 'it'
            finder.replacement = 'xx'
            finder.next()
            finder.replace()
            assert finder.text == \
                'One only risks xx, because\n' \
                'one\'s survival depends on it.'
            finder.next()
            finder.replace()
            assert finder.text == \
                'One only risks xx, because\n' \
                'one\'s survival depends on xx.'

            finder = self.get_finder()
            finder.set_regex(r'\bit\b', re.MULTILINE)
            finder.replacement = 'xx'
            finder.position = len(finder.text)
            finder.previous()
            finder.replace()
            assert finder.text == \
                'One only risks it, because\n' \
                'one\'s survival depends on xx.'
            finder.previous()
            finder.replace()
            assert finder.text == \
                'One only risks xx, because\n' \
                'one\'s survival depends on xx.'

        def test_replace_all(self):

            finder = self.get_finder()
            finder.pattern = 'it'
            finder.replacement = 'xx'
            assert finder.replace_all() == 2
            assert finder.text == \
                'One only risks xx, because\n' \
                'one\'s survival depends on xx.'

            finder = self.get_finder()
            finder.set_regex(r'\bit\b', re.MULTILINE)
            finder.replacement = 'xx'
            assert finder.replace_all() == 2
            assert finder.text == \
                'One only risks xx, because\n' \
                'one\'s survival depends on xx.'

        def test_set_regex(self):

            finder = self.get_finder()
            finder.set_regex('test', re.DOTALL)
            assert finder.is_regex == True
            assert finder.pattern == 'test'
            assert finder.regex.pattern == 'test'
            assert finder.regex.flags == re.UNICODE|re.DOTALL

    TestFinder().run()
