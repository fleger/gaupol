# -*- coding: utf-8 -*-

# Copyright (C) 2005-2008,2010 Osmo Salomaa
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

"""Dialog for selecting a video file."""

import aeidon
_ = aeidon.i18n._

from gi.repository import GObject
from gi.repository import Gtk

__all__ = ("VideoDialog",)


class VideoDialog(Gtk.FileChooserDialog):

    """Dialog for selecting a video file."""

    def __init__(self, parent):
        """Initialize a :class:`VideoDialog` object."""
        GObject.GObject.__init__(self)
        self.set_title(_("Select Video"))
        self.set_transient_for(parent)
        self.set_action(Gtk.FileChooserAction.OPEN)
        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.add_button(_("_Select"), Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self._init_filters()

    def _init_filters(self):
        """Intialize the file filters."""
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern("*")
        file_filter.set_name(_("All files"))
        self.add_filter(file_filter)
        file_filter = Gtk.FileFilter()
        file_filter.add_mime_type("video/*")
        file_filter.set_name(_("Video files"))
        self.add_filter(file_filter)
        self.set_filter(file_filter)
