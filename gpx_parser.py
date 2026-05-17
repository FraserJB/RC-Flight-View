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
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from datetime import datetime

class GPXParser:
    def __init__(self, log_path, progress_callback=None):
        self.log_path = log_path
        self.progress_callback = progress_callback
        self.df_merged = None
        self.ref_lat = None
        self.ref_lon = None
        
        self.firmware_version = "GPX Activity Log"
        self.vehicle_type = "Athlete"
        self.activity_date = "Unknown"
        self.activity_start_time = "Unknown"
        
        self.load_data()
        
    def load_data(self):
        if self.progress_callback: 
            self.progress_callback("Parsing GPX XML...", 20)
        
        tree = ET.parse(self.log_path)
        root = tree.getroot()
        
        ns = {
            'gpx': 'http://www.topografix.com/GPX/1/1',
            'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
        }
        
        # 1. Parse Metadata for Date / Time
        meta_time = root.find('.//gpx:metadata/gpx:time', ns)
        if meta_time is not None and meta_time.text:
            try:
                dt = datetime.strptime(meta_time.text.replace('.000', '').replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                self.activity_date = dt.strftime("%Y-%m-%d")
                self.activity_start_time = dt.strftime("%H:%M:%S UTC")
            except Exception:
                pass
                
        # 2. Parse Trackpoints
        trackpoints = root.findall('.//gpx:trkpt', ns)
        total_pts = len(trackpoints)
        
        pts_data = []
        start_dt = None
        
        for idx, pt in enumerate(trackpoints):
            if self.progress_callback and idx % 200 == 0:
                pct = 20 + int((idx / total_pts) * 50)
                self.progress_callback(f"Extracting trackpoint {idx}/{total_pts}...", pct)
                
            lat = float(pt.attrib.get('lat'))
            lon = float(pt.attrib.get('lon'))
            
            ele_el = pt.find('gpx:ele', ns)
            ele = float(ele_el.text) if ele_el is not None else 0.0
            
            time_el = pt.find('gpx:time', ns)
            time_str = time_el.text if time_el is not None else None
            
            # Garmin TrackPoint Extension (Heart Rate & Cadence)
            hr = np.nan
            cad = np.nan
            
            hr_el = pt.find('.//{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr')
            if hr_el is None:
                hr_el = pt.find('.//hr')
            if hr_el is not None and hr_el.text:
                hr = int(hr_el.text)
                
            cad_el = pt.find('.//{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}cad')
            if cad_el is None:
                cad_el = pt.find('.//cad')
            if cad_el is not None and cad_el.text:
                cad = int(cad_el.text)
                
            time_us = 0
            if time_str:
                clean_time = time_str.replace('.000', '').replace('Z', '')
                try:
                    pt_dt = datetime.strptime(clean_time, "%Y-%m-%dT%H:%M:%S")
                    if start_dt is None:
                        start_dt = pt_dt
                        if self.activity_date == "Unknown":
                            self.activity_date = start_dt.strftime("%Y-%m-%d")
                            self.activity_start_time = start_dt.strftime("%H:%M:%S UTC")
                    
                    time_us = int((pt_dt - start_dt).total_seconds() * 1e6)
                except Exception:
                    if start_dt is None:
                        start_dt = datetime.now()
                    time_us = idx * 1000000
            else:
                time_us = idx * 1000000
                
            pts_data.append({
                'time (us)': time_us,
                'GPS_coord[0]': lat,
                'GPS_coord[1]': lon,
                'GPS_altitude': ele,
                'altitude_m': ele,
                'heart_rate': hr,
                'cadence': cad
            })
            
        if not pts_data:
            raise ValueError("No valid trackpoints found in GPX log.")
            
        # Create initial DataFrame
        df_raw = pd.DataFrame(pts_data)
        df_raw = df_raw.sort_values('time (us)').drop_duplicates(subset=['time (us)']).reset_index(drop=True)
        
        # Fill missing HR/Cadence in the raw data first so they interpolate nicely
        if df_raw['heart_rate'].notna().any():
            df_raw['heart_rate'] = df_raw['heart_rate'].ffill().bfill()
        else:
            df_raw['heart_rate'] = 0.0
            
        if df_raw['cadence'].notna().any():
            df_raw['cadence'] = df_raw['cadence'].ffill().bfill()
        else:
            df_raw['cadence'] = 0.0
            
        # --- Resample to a Constant 1Hz (1,000,000 us) Rate for perfectly smooth playback ---
        max_time_us = df_raw['time (us)'].max()
        new_times_us = np.arange(0, max_time_us + 1000000, 1000000, dtype=int)
        
        resampled_data = {
            'time (us)': new_times_us
        }
        
        for col in df_raw.columns:
            if col == 'time (us)':
                continue
            # Interpolate all columns smoothly
            resampled_data[col] = np.interp(new_times_us, df_raw['time (us)'], df_raw[col])
            
        df = pd.DataFrame(resampled_data)
        
        # Round heart_rate and cadence to integer
        df['heart_rate'] = df['heart_rate'].round().astype(int)
        df['cadence'] = df['cadence'].round().astype(int)
        
        # --- Handle GPS Coordinate Spikes / Erroneous Jumps ---
        R = 6371000.0
        
        lats_rad = np.radians(df['GPS_coord[0]'])
        lons_rad = np.radians(df['GPS_coord[1]'])
        
        dlat = lats_rad.diff().fillna(0)
        dlon = lons_rad.diff().fillna(0)
        
        lat_mid = lats_rad.shift(1).fillna(lats_rad.iloc[0])
        dx = R * dlon * np.cos(lat_mid)
        dy = R * dlat
        dist_step = np.sqrt(dx**2 + dy**2)
        
        dt_sec = df['time (us)'].diff().fillna(0) / 1e6
        
        # Reject coordinates where speed > 25 m/s (approx 90 km/h)
        erroneous_mask = (dt_sec > 0) & ((dist_step / dt_sec) > 25.0)
        
        if erroneous_mask.any():
            for i in range(1, len(df)):
                if erroneous_mask.iloc[i]:
                    df.loc[i, 'GPS_coord[0]'] = df.loc[i-1, 'GPS_coord[0]']
                    df.loc[i, 'GPS_coord[1]'] = df.loc[i-1, 'GPS_coord[1]']
                    
            # Recalculate steps
            lats_rad = np.radians(df['GPS_coord[0]'])
            lons_rad = np.radians(df['GPS_coord[1]'])
            dlat = lats_rad.diff().fillna(0)
            dlon = lons_rad.diff().fillna(0)
            lat_mid = lats_rad.shift(1).fillna(lats_rad.iloc[0])
            dx = R * dlon * np.cos(lat_mid)
            dy = R * dlat
            dist_step = np.sqrt(dx**2 + dy**2)
            
        df['distance_m'] = dist_step.cumsum()
        
        # Raw speed
        raw_speed = dist_step / dt_sec.replace(0, 1)
        raw_speed.iloc[0] = 0
        raw_speed = raw_speed.clip(upper=25.0)
        
        # --- Smooth Speed, Altitude, and Slope ---
        window_size = 15
        df['GPS_speed (m/s)'] = raw_speed.rolling(window=window_size, min_periods=1, center=True).mean()
        
        # Calculate Pace (min/km)
        df['pace (min/km)'] = 1000.0 / (df['GPS_speed (m/s)'].replace(0, np.nan) * 60.0)
        df['pace (min/km)'] = df['pace (min/km)'].fillna(20.0).clip(upper=20.0)
        
        dz = df['altitude_m'].diff().fillna(0)
        df['altitude_m'] = df['altitude_m'].rolling(window=10, min_periods=1, center=True).mean()
        dz_smooth = df['altitude_m'].diff().fillna(0)
        
        # Calculate cumulative height gain (total positive elevation change)
        df['cumulative_gain_m'] = np.maximum(dz_smooth, 0.0).cumsum()
        
        raw_slope = (dz_smooth / dist_step.replace(0, 1.0)) * 100.0
        raw_slope.iloc[0] = 0.0
        df['slope (%)'] = raw_slope.rolling(window=15, min_periods=1, center=True).mean().clip(lower=-30.0, upper=30.0)
        
        raw_climb = (dz_smooth / dt_sec.replace(0, 1.0)) * 60.0
        raw_climb.iloc[0] = 0.0
        df['climb_rate (m/min)'] = raw_climb.rolling(window=15, min_periods=1, center=True).mean()
        
        s_frac = df['slope (%)'] / 100.0
        gap_factors = np.where(
            s_frac >= 0,
            1.0 + 3.5 * s_frac + 10.0 * s_frac**2,
            1.0 + 1.5 * s_frac + 5.0 * s_frac**2
        )
        gap_speed = df['GPS_speed (m/s)'] * gap_factors
        df['GAP (min/km)'] = 1000.0 / (gap_speed.replace(0, np.nan) * 60.0)
        df['GAP (min/km)'] = df['GAP (min/km)'].fillna(20.0).clip(upper=20.0)
        
        cadence_replace = df['cadence'].replace(0, np.nan)
        df['stride_length (m)'] = df['GPS_speed (m/s)'] / (cadence_replace / 120.0)
        df['stride_length (m)'] = df['stride_length (m)'].fillna(0.0).clip(upper=3.0)
        
        self.df_merged = df
        self.calculate_local_coordinates()
        
    def calculate_local_coordinates(self):
        if self.progress_callback: 
            self.progress_callback("Calculating local coordinates...", 80)
            
        R = 6371000.0
        lat = np.radians(self.df_merged['GPS_coord[0]'])
        lon = np.radians(self.df_merged['GPS_coord[1]'])
        alt = self.df_merged['altitude_m']
        
        self.ref_lat = lat.iloc[0]
        self.ref_lon = lon.iloc[0]
        ref_alt = alt.iloc[0]
        
        self.df_merged['pos_x'] = R * (lon - self.ref_lon) * np.cos(self.ref_lat)
        self.df_merged['pos_y'] = R * (lat - self.ref_lat)
        self.df_merged['pos_z'] = alt - ref_alt
        
        dx = self.df_merged['pos_x'].diff().fillna(0)
        dy = self.df_merged['pos_y'].diff().fillna(0)
        
        heading = np.degrees(np.arctan2(dx, dy)) % 360
        df_heading = pd.Series(heading).rolling(window=10, min_periods=1, center=True).mean().fillna(0.0)
        
        self.df_merged['attitude[0]'] = 0.0
        self.df_merged['attitude[1]'] = 0.0
        self.df_merged['attitude[2]'] = df_heading
        
    def get_data(self):
        return self.df_merged
        
    def get_bounds(self):
        if 'GPS_coord[0]' not in self.df_merged.columns:
            return None
        return (self.df_merged['GPS_coord[0]'].min(), self.df_merged['GPS_coord[0]'].max(),
                self.df_merged['GPS_coord[1]'].min(), self.df_merged['GPS_coord[1]'].max())
                
    def latlon_to_local(self, lat_deg, lon_deg):
        R = 6371000.0
        lat_rad = np.radians(lat_deg)
        lon_rad = np.radians(lon_deg)
        
        x = R * (lon_rad - self.ref_lon) * np.cos(self.ref_lat)
        y = R * (lat_rad - self.ref_lat)
        return x, y
