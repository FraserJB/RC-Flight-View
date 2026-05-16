# Copyright (C) 2026 Fraser Boyd
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import pandas as pd

sys.path.insert(0, r"C:\00Fraser\AI Projects\RC Flight View")
from data_parser import detect_and_parse

log_path = r"C:\00Fraser\AI Projects\RC Flight View\Logs - Ardu\ArduPlane-TerrainMission-00000057.BIN"

parser, log_type = detect_and_parse(log_path)
df = parser.get_data()

print(df[['GPS_numSat', 'GPS_hdop']].describe())
