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
import os
import pandas as pd
import numpy as np

sys.path.insert(0, r"C:\00Fraser\AI Projects\RC Flight View")
from data_parser import detect_and_parse

log_path = r"C:\00Fraser\AI Projects\RC Flight View\Logs - Ardu\ArduPlane-TerrainMission-00000057.BIN"

print(f"Loading {log_path}...")
parser, log_type = detect_and_parse(log_path)
df = parser.get_data()

print(f"\nLog type: {log_type}")
print(f"Total rows: {len(df)}")

print("\n--- GPS Analysis ---")
gps_cols = [c for c in df.columns if 'GPS' in c or 'pos' in c]
print("Available GPS columns:", gps_cols)

print("\nFirst 10 rows of GPS data:")
print(df[['time (us)', 'GPS_coord[0]', 'GPS_coord[1]', 'pos_x', 'pos_y', 'pos_z']].head(10).to_string())

print("\nLast 10 rows of GPS data:")
print(df[['time (us)', 'GPS_coord[0]', 'GPS_coord[1]', 'pos_x', 'pos_y', 'pos_z']].tail(10).to_string())

print("\nSummary of coordinates:")
print("pos_x min/max:", df['pos_x'].min(), df['pos_x'].max())
print("pos_y min/max:", df['pos_y'].min(), df['pos_y'].max())
print("pos_z min/max:", df['pos_z'].min(), df['pos_z'].max())
print("GPS_coord[0] min/max:", df['GPS_coord[0]'].min(), df['GPS_coord[0]'].max())
print("GPS_coord[1] min/max:", df['GPS_coord[1]'].min(), df['GPS_coord[1]'].max())

print("\nReference point used:")
print("ref_lat (deg):", np.degrees(parser.ref_lat))
print("ref_lon (deg):", np.degrees(parser.ref_lon))

# Let's see how many were NaN before ffill
bad_gps = (df['GPS_coord[0]'] == 0) & (df['GPS_coord[1]'] == 0)
print("\nNumber of rows with raw (0,0):", bad_gps.sum())
if 'GPS_numSat' in df.columns:
    low_sats = df['GPS_numSat'] < 6
    print("Number of rows with < 6 sats:", low_sats.sum())
