# -*- coding: utf-8 -*-

# Copyright (C) 2009-2010 Osmo Salomaa
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

"""Cell renderer for float data with fixed precision."""

import aeidon

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

__all__ = ("FloatCellRenderer",)


class FloatCellRenderer(Gtk.CellRendererText):

    """Cell renderer for float data with fixed precision."""

    __gtype_name__ = "FloatCellRenderer"

    def __init__(self, format="{:.3f}"):
        """Initialize a :class:`FloatCellRenderer` object."""
        GObject.GObject.__init__(self)
        self._format = format
        self._text = ""
        aeidon.util.connect(self, self, "notify::text")
        aeidon.util.connect(self, self, "editing-started")

    def _on_editing_started(self, renderer, editor, path):
        """Set `editor` to use same font as `self`."""
        editor.modify_font(self.props.font_desc)

    def _on_notify_text(self, *args):
        """Cut decimals to fixed precision."""
        self._text = text = self.props.text
        if not text: return
        has_comma = text.find(",") > 0
        text = text.replace(",", ".")
        text = self._format.format(float(text))
        text = (text.replace(".", ",") if has_comma else text)
        self.props.markup = GLib.markup_escape_text(text)
