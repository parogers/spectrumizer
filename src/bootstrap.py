# Spectrumizer - Tools for spectrum capture and analysis
# Copyright (C) 2017 Peter Rogers (peter.rogers@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import site
import django

def setup_django():
    # Setup the environment for django, so we can use the object model code for
    # interfacing with the database.
    os.environ["DJANGO_SETTINGS_MODULE"] = "spectrumweb.settings"

    path = os.path.join(os.path.dirname(sys.argv[0]), "spectrumweb")
    site.addsitedir(path)

    django.setup()
