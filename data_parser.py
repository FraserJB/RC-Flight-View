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

import os
import sys
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime

def get_app_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class BlackboxDecodeMissingError(Exception):
    pass

class DataParser:
    def __init__(self, log_path, decode_exe_path=None, progress_callback=None):
        self.log_path = log_path
        self.decode_exe_path = decode_exe_path
        self.progress_callback = progress_callback
        self.main_csv = None
        self.gps_csv = None
        self.df_main = None
        self.df_gps = None
        self.df_merged = None
        self.ref_lat = None
        self.ref_lon = None
        
        self.firmware_version = "Unknown"
        self._extract_firmware_version()
        
        self.decode_log()
        self.load_data()

    def _extract_firmware_version(self):
        """Attempts to read the firmware version from the raw blackbox log header."""
        # Find the raw log path (might be the same as self.log_path or a related .TXT file)
        raw_path = self.log_path
        if raw_path.lower().endswith('.csv'):
            # Try to find a .TXT file with the same base name
            base = raw_path.split('.01.csv')[0]
            for ext in ['.TXT', '.txt', '.BBL', '.bbl']:
                if os.path.exists(base + ext):
                    raw_path = base + ext
                    break
        
        if not os.path.exists(raw_path) or raw_path.lower().endswith('.csv'):
            return

        try:
            with open(raw_path, 'r', errors='ignore') as f:
                for _ in range(100): # Scan first 100 lines
                    line = f.readline()
                    if not line: break
                    if "Firmware revision:" in line:
                        # Format: H Firmware revision:INAV 7.1.2 (4e1e59eb) ...
                        version_str = line.split("revision:", 1)[1].strip()
                        if "INAV" in version_str:
                            # Extract just the INAV X.Y.Z part
                            parts = version_str.split(" ")
                            self.firmware_version = f"{parts[0]} {parts[1]}"
                        else:
                            self.firmware_version = version_str.split(" ")[0]
                        break
        except Exception:
            pass

    def decode_log(self):
        """Decodes the binary log file to CSV using blackbox_decode.exe if necessary."""
        base_name = os.path.splitext(self.log_path)[0]
        self.main_csv = f"{base_name}.01.csv"
        self.gps_csv = f"{base_name}.01.gps.csv"
        
        if not os.path.exists(self.main_csv):
            if self.progress_callback: self.progress_callback("Decoding log file with blackbox_decode...", 10)
            print(f"Decoding {self.log_path}...")
            if not self.decode_exe_path:
                base_path = get_app_base_path()
                decode_exe = os.path.join(base_path, "blackbox-tools", "bin", "blackbox_decode.exe")
            else:
                decode_exe = self.decode_exe_path
            
            if not os.path.exists(decode_exe):
                raise BlackboxDecodeMissingError(f"blackbox_decode.exe not found at {decode_exe}")
            
            # Run decoding
            try:
                kwargs = {'check': True, 'capture_output': True}
                if os.name == 'nt':
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                subprocess.run([decode_exe, self.log_path], **kwargs)
            except subprocess.CalledProcessError as e:
                err_msg = f"Error decoding log '{self.log_path}'.\n\nTool output:\n{e.stderr.decode(errors='ignore')}\n{e.stdout.decode(errors='ignore')}"
                print(err_msg)
                raise Exception(err_msg)

    def load_data(self):
        """Loads and processes the decoded CSV files."""
        if self.progress_callback: self.progress_callback("Loading main CSV data...", 40)
        self.df_main = pd.read_csv(self.main_csv).drop_duplicates(subset=['time (us)'])
        
        if os.path.exists(self.gps_csv):
            if self.progress_callback: self.progress_callback("Loading and merging GPS data...", 60)
            self.df_gps = pd.read_csv(self.gps_csv).drop_duplicates(subset=['time (us)'])
            # Merge GPS data into main dataframe by interpolating timestamps
            # GPS data is usually lower frequency than blackbox data
            self.df_merged = self.merge_gps_data()
        else:
            self.df_merged = self.df_main.copy()
            # If no GPS, we might just have baro alt
            if 'BaroAlt (cm)' in self.df_merged.columns:
                self.df_merged['altitude_m'] = self.df_merged['BaroAlt (cm)'] / 100.0
            else:
                self.df_merged['altitude_m'] = 0.0

        # Pre-calculate local coordinates (X, Y in meters)
        if 'GPS_coord[0]' in self.df_merged.columns:
            self.calculate_local_coordinates()
        else:
            self.df_merged['pos_x'] = 0.0
            self.df_merged['pos_y'] = 0.0
            self.df_merged['pos_z'] = self.df_merged.get('altitude_m', 0.0)

        # Basic INAV deci-unit conversions
        new_cols = {}
        for col in ['attitude[0]', 'attitude[1]', 'attitude[2]']:
            if col in self.df_merged.columns:
                new_cols[col] = self.df_merged[col] / 10.0
                
        for temp_col in ['IMUTemperature', 'baroTemperature', 'escTemperature']:
            if temp_col in self.df_merged.columns:
                new_cols[temp_col] = self.df_merged[temp_col] / 10.0
                
        if new_cols:
            self.df_merged = self.df_merged.assign(**new_cols)

    def merge_gps_data(self):
        """Merges GPS data into the main dataframe using interpolation."""
        # Clean columns names for easier access
        self.df_main.columns = [c.strip() for c in self.df_main.columns]
        self.df_gps.columns = [c.strip() for c in self.df_gps.columns]
        
        # Use 'time (us)' as the common key
        # Create a combined index of all timestamps
        all_times = sorted(list(set(self.df_main['time (us)']).union(set(self.df_gps['time (us)']))))
        
        # Reindex and interpolate GPS data
        df_gps_interp = self.df_gps.set_index('time (us)').reindex(all_times).interpolate(method='index')
        df_gps_interp = df_gps_interp.loc[self.df_main['time (us)']]
        
        # Combine
        merged = pd.concat([self.df_main.reset_index(drop=True), df_gps_interp.reset_index(drop=True)], axis=1)
        # Drop duplicate columns
        merged = merged.loc[:,~merged.columns.duplicated()]
        # Defragment
        merged = merged.copy()
        
        # Fill NaNs in GPS columns (important for start/end of log)
        gps_cols = [c for c in self.df_gps.columns if c != 'time (us)']
        merged[gps_cols] = merged[gps_cols].ffill().bfill()
        
        return merged

    def calculate_local_coordinates(self):
        """Converts Lat/Lon/Alt to local Cartesian meters (relative to start)."""
        if self.progress_callback: self.progress_callback("Calculating local coordinates...", 80)
        # Earth radius in meters
        R = 6371000.0
        
        lat = np.radians(self.df_merged['GPS_coord[0]'])
        lon = np.radians(self.df_merged['GPS_coord[1]'])
        alt = self.df_merged['GPS_altitude'] # Assuming this is in meters
        
        # Reference point (start of flight)
        # Use mean of first few rows for stability
        self.ref_lat = lat.iloc[:10].mean()
        self.ref_lon = lon.iloc[:10].mean()
        ref_alt = alt.iloc[:10].mean()
        
        # Calculate all new columns at once to avoid PerformanceWarning (fragmentation)
        new_cols = {}
        new_cols['pos_x'] = R * (lon - self.ref_lon) * np.cos(self.ref_lat)
        new_cols['pos_y'] = R * (lat - self.ref_lat)
        new_cols['pos_z'] = alt - ref_alt
        
        # Apply all at once
        self.df_merged = self.df_merged.assign(**new_cols)
        
        # Smooth coordinates to prevent "jumping"
        # Window size 200 (approx 200ms at 1kHz) matches GPS update rate
        for col in ['pos_x', 'pos_y', 'pos_z']:
            self.df_merged[col] = self.df_merged[col].rolling(window=200, min_periods=1, center=True).mean()
        
        # Ensure no NaNs in critical columns
        self.df_merged[['pos_x', 'pos_y', 'pos_z']] = self.df_merged[['pos_x', 'pos_y', 'pos_z']].ffill().bfill().fillna(0.0)
        
        # De-fragment and print ref
        self.df_merged = self.df_merged.reset_index(drop=True).copy()

    def get_data(self):
        return self.df_merged

    def get_bounds(self):
        """Returns (min_lat, max_lat, min_lon, max_lon)"""
        if 'GPS_coord[0]' not in self.df_merged.columns:
            return None
        return (self.df_merged['GPS_coord[0]'].min(), self.df_merged['GPS_coord[0]'].max(),
                self.df_merged['GPS_coord[1]'].min(), self.df_merged['GPS_coord[1]'].max())

    def latlon_to_local(self, lat_deg, lon_deg):
        """Converts arbitrary Lat/Lon to local XY."""
        R = 6371000.0
        lat_rad = np.radians(lat_deg)
        lon_rad = np.radians(lon_deg)
        
        x = R * (lon_rad - self.ref_lon) * np.cos(self.ref_lat)
        y = R * (lat_rad - self.ref_lat)
        return x, y

def detect_log_type(file_path):
    """
    Detect whether a log file is INAV Blackbox, ArduPilot DataFlash, or EdgeTX Telemetry.
    Returns 'inav', 'ardupilot', or 'edgetx'.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.gpx':
        return 'gpx'

    # .BIN files are always ArduPilot DataFlash
    if ext == '.bin':
        return 'ardupilot'

    # .TXT or .BBL — check the header for INAV Blackbox signature
    if ext in ('.txt', '.bbl', '.csv', ''):
        try:
            with open(file_path, 'r', errors='ignore') as f:
                header = f.read(1024)
            if 'Blackbox flight data recorder' in header or 'H Product:' in header:
                return 'inav'
            
            # EdgeTX logs start with Date,Time
            if header.startswith('Date,Time'):
                return 'edgetx'
        except Exception:
            pass

    # Fallback: try reading as ArduPilot binary
    try:
        with open(file_path, 'rb') as f:
            magic = f.read(3)
        # ArduPilot DataFlash binary starts with specific byte patterns
        if magic[:2] in (b'\xa3\x95', b'\x95\xa3'):
            return 'ardupilot'
    except Exception:
        pass

    # Default to INAV for .TXT/.BBL
    return 'inav'


def detect_and_parse(file_path, decode_exe_path=None, progress_callback=None):
    """
    Factory function: detects log type and returns the appropriate parser.
    Returns (parser_instance, log_type_string).
    """
    log_type = detect_log_type(file_path)

    if log_type == 'ardupilot':
        from ardupilot_parser import ArdupilotParser
        parser = ArdupilotParser(file_path, progress_callback=progress_callback)
        return parser, 'ardupilot'
    elif log_type == 'edgetx':
        from edgetx_parser import EdgeTXParser
        parser = EdgeTXParser(file_path, progress_callback=progress_callback)
        return parser, 'edgetx'
    elif log_type == 'gpx':
        from gpx_parser import GPXParser
        parser = GPXParser(file_path, progress_callback=progress_callback)
        return parser, 'gpx'



    else:
        parser = DataParser(file_path, decode_exe_path=decode_exe_path,
                            progress_callback=progress_callback)
        return parser, 'inav'


if __name__ == "__main__":
    # Test
    parser = DataParser("LOG00054.TXT")
    data = parser.get_data()
    print(data[['time (us)', 'pos_x', 'pos_y', 'pos_z']].head())
