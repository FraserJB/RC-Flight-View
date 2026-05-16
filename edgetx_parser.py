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
import numpy as np
import pandas as pd
from datetime import datetime

class EdgeTXParser:
    """
    Parses EdgeTX Telemetry CSV logs and produces a normalised
    Pandas DataFrame compatible with the application's internal schema.
    """

    def __init__(self, log_path, progress_callback=None):
        self.log_path = log_path
        self.progress_callback = progress_callback
        self.firmware_version = "EdgeTX Telemetry"
        self.ref_lat = None
        self.ref_lon = None
        self.df_merged = None
        
        self._parse()

    def get_data(self):
        return self.df_merged

    def get_bounds(self):
        """Returns (min_lat, max_lat, min_lon, max_lon) or None."""
        if self.df_merged is None or 'GPS_coord[0]' not in self.df_merged.columns:
            return None
        coords = self.df_merged[['GPS_coord[0]', 'GPS_coord[1]']].apply(pd.to_numeric, errors='coerce').dropna()
        if coords.empty:
            return None
        return (
            coords['GPS_coord[0]'].min(),
            coords['GPS_coord[0]'].max(),
            coords['GPS_coord[1]'].min(),
            coords['GPS_coord[1]'].max(),
        )

    def latlon_to_local(self, lat_deg, lon_deg):
        R = 6371000.0
        lat_rad = np.radians(lat_deg)
        lon_rad = np.radians(lon_deg)
        x = R * (lon_rad - self.ref_lon) * np.cos(self.ref_lat)
        y = R * (lat_rad - self.ref_lat)
        return x, y

    def _parse(self):
        if self.progress_callback:
            self.progress_callback("Reading EdgeTX CSV...", 10)

        # Load the CSV
        df = pd.read_csv(self.log_path)
        
        # Clean column names (strip whitespace)
        df.columns = [c.strip() for c in df.columns]

        if self.progress_callback:
            self.progress_callback("Processing timestamps...", 30)

        # 1. Create 'time (us)' from Date and Time
        # Try to parse Date and Time
        # Some logs have Date as YYYY-MM-DD, others DD/MM/YYYY
        # Some logs have Time as HH:MM:SS.mmm, others MM:SS.s
        
        def parse_timestamp(row):
            d_str = str(row['Date'])
            t_str = str(row['Time'])
            
            # If Time is just MM:SS.s, we need to handle it.
            # Usually EdgeTX logs are consistent within a file.
            # We'll try a few common formats.
            
            # Prepend a dummy date if needed or use the Date column
            # If Date is empty, use 2000-01-01
            if not d_str or d_str == 'nan':
                d_str = '2000-01-01'
            
            # Check if t_str has hours (contains two colons)
            if t_str.count(':') == 1:
                # MM:SS.s format. Assume 00 hours.
                t_str = "00:" + t_str
            
            try:
                # Try YYYY-MM-DD
                return pd.to_datetime(d_str + " " + t_str)
            except:
                try:
                    # Try DD/MM/YYYY
                    return pd.to_datetime(d_str + " " + t_str, dayfirst=True)
                except:
                    # Fallback to just Time relative to a start
                    return pd.to_datetime("2000-01-01 " + t_str)

        # More efficient: build timestamp strings and use pd.to_datetime on the series
        time_strings = df['Date'].astype(str) + " " + df['Time'].astype(str)
        # Fix MM:SS.s cases in the series
        mask_short_time = ~df['Time'].astype(str).str.contains(r'\d+:\d+:\d+')
        time_strings.loc[mask_short_time] = df['Date'].astype(str) + " 00:" + df['Time'].astype(str)
        
        try:
            date_text = df['Date'].astype(str).str.strip()
            iso_dates = date_text.str.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$', na=False)
            dayfirst = not iso_dates.mean() > 0.5
            df['datetime'] = pd.to_datetime(time_strings, errors='coerce', dayfirst=dayfirst)
        except:
            # Last resort: row by row (slow)
            df['datetime'] = df.apply(parse_timestamp, axis=1)
            
        # If still NaTs, fill them
        df['datetime'] = df['datetime'].ffill().bfill()
        
        # Convert to microseconds relative to start
        start_dt = df['datetime'].iloc[0]
        df['time (us)'] = (df['datetime'] - start_dt).dt.total_seconds() * 1e6

        if self.progress_callback:
            self.progress_callback("Mapping telemetry fields...", 50)

        # 2. Map GPS
        if 'GPS' in df.columns:
            # Format is usually "lat lon"
            # Strip and split by any whitespace
            gps_split = df['GPS'].astype(str).str.strip().str.split(r'\s+', expand=True)
            if gps_split.shape[1] >= 2:
                df['lat'] = pd.to_numeric(gps_split[0], errors='coerce')
                df['lon'] = pd.to_numeric(gps_split[1], errors='coerce')
                
                valid_coord = (
                    df['lat'].between(-90, 90) &
                    df['lon'].between(-180, 180) &
                    (df['lat'] != 0) &
                    (df['lon'] != 0)
                )
                df.loc[~valid_coord, ['lat', 'lon']] = np.nan
                
                # Copy raw valid coordinates to internal names.  Confidence and
                # interpolation are handled after GPS_numSat is normalised.
                df['GPS_coord[0]'] = df['lat']
                df['GPS_coord[1]'] = df['lon']
        
        # 3. Map common telemetry names to INAV/Ardu names
        rename_map = {
            'Alt(m)': 'GPS_altitude',
            'GAlt(m)': 'BaroAlt (cm)', # Scaled below
            'Alt': 'GPS_altitude',
            'Sats': 'GPS_numSat',
            'GSpd(m/s)': 'GPS_speed (m/s)',
            'GSpd(mph)': 'GPS_speed_mph', # Converted below
            'mph': 'GPS_speed_mph',
            'Hdg(@)': 'GPS_ground_course',
            'RxBt(V)': 'vbat (V)',
            'VFAS(V)': 'vbat (V)',
            'Curr(A)': 'amperage (A)',
            'CURR(A)': 'amperage (A)',
            'Capa(mAh)': 'energyCumulative (mAh)',
            'Fuel(%)': 'batteryRemaining',
            'RSSI(dB)': 'rssi',
            '1RSS(dB)': 'rssi',
            'TRSS(dB)': 'rssi_tx',
            'TQly': 'linkQuality',
            'RQly(%)': 'linkQuality',
            'Ptch(rad)': 'pitch_rad',
            'Roll(rad)': 'roll_rad',
            'Yaw(rad)': 'yaw_rad',
        }
        
        # Apply renaming for columns that exist
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Handle duplicate columns after renaming (e.g. both VFAS and RxBt might exist)
        # We'll keep the first one and drop others to avoid Series conversion in stats
        duplicated_cols = df.columns[df.columns.duplicated()]
        if not duplicated_cols.empty:
            df = df.loc[:, ~df.columns.duplicated()]

        # Interpolate altitude and other sparse sensors if they exist
        for col in ['GPS_altitude', 'BaroAlt (cm)', 'vbat (V)', 'amperage (A)', 'GPS_speed (m/s)', 'GPS_speed_mph']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').interpolate(method='linear', limit_direction='both')

        # 4. Unit conversions
        if 'BaroAlt (cm)' in df.columns:
            # If it came from GAlt(m), it's in meters. Internal schema uses cm.
            df['BaroAlt (cm)'] = df['BaroAlt (cm)'] * 100.0
            
        if 'GPS_speed_mph' in df.columns and 'GPS_speed (m/s)' not in df.columns:
            df['GPS_speed (m/s)'] = df['GPS_speed_mph'] * 0.44704
            
        # Radian to Degree for attitude
        for ax in ['pitch', 'roll', 'yaw']:
            col = f"{ax}_rad"
            target = f"attitude[{['roll', 'pitch', 'yaw'].index(ax)}]"
            if col in df.columns:
                df[target] = np.degrees(df[col])
                
        # 5. RC Data mapping
        rc_map = {
            'Ail': 'rcData[0]',
            'Ele': 'rcData[1]',
            'Rud': 'rcData[2]',
            'Thr': 'rcData[3]',
        }
        df = df.rename(columns={k: v for k, v in rc_map.items() if k in df.columns})
        
        # Scale RC data from EdgeTX (-1024..1024) to INAV (1000..2000)
        # Formula: ((val + 1024) / 2048) * 1000 + 1000
        for i in range(4):
            col = f'rcData[{i}]'
            if col in df.columns:
                df[col] = ((df[col] + 1024) / 2048.0) * 1000.0 + 1000.0

        # 6. Flight Mode
        if 'FM' in df.columns:
            # FM is numeric in EdgeTX. 
            # We don't have a lookup table for user-defined modes, so just use "MODE_X"
            df['flightModeFlags (flags)'] = df['FM'].apply(lambda x: f"MODE_{int(x)}" if pd.notna(x) else "UNKNOWN")
        else:
            df['flightModeFlags (flags)'] = "UNKNOWN"

        if self.progress_callback:
            self.progress_callback("Calculating local coordinates...", 80)

        # 7. Local Coordinates
        if 'GPS_coord[0]' in df.columns and 'GPS_coord[1]' in df.columns:
            self._calculate_local_coordinates(df)
        else:
            df['pos_x'] = 0.0
            df['pos_y'] = 0.0
            df['pos_z'] = df.get('GPS_altitude', 0.0)

        self.df_merged = df
        if self.progress_callback:
            self.progress_callback("EdgeTX log loaded.", 100)

    def _calculate_local_coordinates(self, df):
        # Earth radius in meters
        R = 6371000.0
        
        # 1. Build a validity mask
        # Filter out invalid (0,0) coordinates and NaNs
        df['GPS_coord[0]'] = pd.to_numeric(df['GPS_coord[0]'], errors='coerce')
        df['GPS_coord[1]'] = pd.to_numeric(df['GPS_coord[1]'], errors='coerce')
        valid_gps_mask = (
            df['GPS_coord[0]'].between(-90, 90) &
            df['GPS_coord[1]'].between(-180, 180) &
            (df['GPS_coord[0]'] != 0) &
            (df['GPS_coord[1]'] != 0)
        )
        
        # If available, also filter by satellite count (EdgeTX 'Sats' -> 'GPS_numSat')
        if 'GPS_numSat' in df.columns:
            sats = pd.to_numeric(df['GPS_numSat'], errors='coerce')
            strong_sat_mask = sats >= 6
            positive_sat_mask = sats > 0

            # Use the best confidence available in the log.  Some EdgeTX logs in
            # the sample set never reach 6 sats but still contain usable GPS
            # once the receiver reports a positive satellite count.
            if (valid_gps_mask & strong_sat_mask).any():
                valid_gps_mask &= strong_sat_mask
            elif (valid_gps_mask & positive_sat_mask).any():
                valid_gps_mask &= positive_sat_mask

        if not valid_gps_mask.any():
            df['pos_x'] = 0.0
            df['pos_y'] = 0.0
            df['pos_z'] = self._get_altitude_series(df) * 0.0
            df[['GPS_coord[0]', 'GPS_coord[1]']] = np.nan
            return

        lat_all = np.radians(df['GPS_coord[0]'])
        lon_all = np.radians(df['GPS_coord[1]'])
        alt_all = self._get_altitude_series(df)
        
        # 2. Determine robust reference point using MEDIAN of valid points
        # This prevents the trace from jumping if the first/last points are glitches.
        valid_lats = lat_all[valid_gps_mask]
        valid_lons = lon_all[valid_gps_mask]
        
        self.ref_lat = valid_lats.median()
        self.ref_lon = valid_lons.median()
        
        # For altitude reference, use the mean of the first few valid points
        valid_alts = alt_all[valid_gps_mask]
        ref_alt = valid_alts.iloc[:10].mean() if not valid_alts.empty else 0.0
        
        # 3. Calculate raw local coordinates
        df['pos_x'] = R * (lon_all - self.ref_lon) * np.cos(self.ref_lat)
        df['pos_y'] = R * (lat_all - self.ref_lat)
        df['pos_z'] = alt_all - ref_alt
        
        # 4. Filter out extreme outliers (e.g. > 100km from the median center)
        dist_sq = df['pos_x']**2 + df['pos_y']**2
        outlier_mask = dist_sq > (100000**2) 
        
        # 5. Mask bad points
        bad_mask = (~valid_gps_mask) | outlier_mask
        df.loc[bad_mask, ['pos_x', 'pos_y', 'pos_z']] = np.nan
        df.loc[bad_mask, ['GPS_coord[0]', 'GPS_coord[1]']] = np.nan
        
        # 6. Fill/Interpolate to provide a continuous path
        df[['pos_x', 'pos_y', 'pos_z']] = df[['pos_x', 'pos_y', 'pos_z']].interpolate(method='linear', limit_direction='both').ffill().bfill().fillna(0.0)
        df[['GPS_coord[0]', 'GPS_coord[1]']] = df[['GPS_coord[0]', 'GPS_coord[1]']].interpolate(method='linear', limit_direction='both').ffill().bfill()
        
        # If entire log was NaNs (shouldn't happen given .any() check above), fallback
        if df['GPS_coord[0]'].isna().all():
            df['GPS_coord[0]'] = np.degrees(self.ref_lat)
            df['GPS_coord[1]'] = np.degrees(self.ref_lon)

    def _get_altitude_series(self, df):
        if 'GPS_altitude' in df.columns:
            return pd.to_numeric(df['GPS_altitude'], errors='coerce').fillna(0.0)
        if 'BaroAlt (cm)' in df.columns:
            return pd.to_numeric(df['BaroAlt (cm)'], errors='coerce').fillna(0.0) / 100.0
        return pd.Series(0.0, index=df.index)
