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

"""
ArduPilot DataFlash (.BIN) log parser.

Parses ArduPilot binary logs using pymavlink and produces a normalised
Pandas DataFrame with the same column names used by the INAV parser,
so all downstream UI code works without modification.
"""

import os
import numpy as np
import pandas as pd
from pymavlink import mavutil


# ── ArduPilot flight-mode tables ─────────────────────────────────────────
ARDUPLANE_MODES = {
    0: "MANUAL", 1: "CIRCLE", 2: "STABILIZE", 3: "TRAINING",
    4: "ACRO", 5: "FLY_BY_WIRE_A", 6: "FLY_BY_WIRE_B", 7: "CRUISE",
    8: "AUTOTUNE", 10: "AUTO", 11: "RTL", 12: "LOITER",
    13: "TAKEOFF", 14: "AVOID_ADSB", 15: "GUIDED",
    17: "QSTABILIZE", 18: "QHOVER", 19: "QLOITER",
    20: "QLAND", 21: "QRTL", 22: "QAUTOTUNE", 23: "QACRO",
    24: "THERMAL", 25: "LOITER_ALT_QLAND",
}

ARDUCOPTER_MODES = {
    0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
    9: "LAND", 11: "DRIFT", 13: "SPORT", 14: "FLIP",
    15: "AUTOTUNE", 16: "POSHOLD", 17: "BRAKE", 18: "THROW",
    19: "AVOID_ADSB", 20: "GUIDED_NOGPS", 21: "SMART_RTL",
    22: "FLOWHOLD", 23: "FOLLOW", 24: "ZIGZAG", 25: "SYSTEMID",
    26: "AUTOROTATE", 27: "AUTO_RTL",
}

ARDUROVER_MODES = {
    0: "MANUAL", 1: "ACRO", 3: "STEERING", 4: "HOLD",
    5: "LOITER", 6: "FOLLOW", 7: "SIMPLE",
    10: "AUTO", 11: "RTL", 12: "SMART_RTL", 15: "GUIDED",
}

# Map vehicle type string (from MSG) to the correct mode table
VEHICLE_MODE_TABLES = {
    "ArduPlane":  ARDUPLANE_MODES,
    "ArduCopter": ARDUCOPTER_MODES,
    "APMrover2":  ARDUROVER_MODES,
    "Rover":      ARDUROVER_MODES,
}

# Category tables for dynamic channel mapping.  Numbered motor functions are
# mapped by their ArduPilot motor identity, not by physical output order.
MOTOR_FUNCTION_TO_INDEX = {
    **{func: func - 33 for func in range(33, 41)},      # Motor1..Motor8
    **{func: func - 82 + 8 for func in range(82, 86)},  # Motor9..Motor12
    **{func: func - 160 + 12 for func in range(160, 180)}, # Motor13..Motor32
}

THROTTLE_FUNCTIONS = {
    70: 0,  # Throttle
    73: 0,  # Throttle Left
    74: 1,  # Throttle Right
    81: 0,  # Boost Engine Throttle
}

MOTOR_FUNCTIONS = set(MOTOR_FUNCTION_TO_INDEX) | set(THROTTLE_FUNCTIONS)

SERVO_FUNCTIONS = {
    2, 3, 4, 16, 17, 18, 19, 20, 21, 24, 25, 26, # Plane surfaces/steering
    41, 45, 46, 47, 75, 76,         # Tilt motors/servos (user preference as servos)
    77, 78, 79, 80,                 # Elevons, V-Tails
    6, 7, 8, 9, 12, 13, 14, 15,     # Mount/gimbal outputs
    27, 28, 29, 88,                 # Parachute, gripper, landing gear, winch
}

SERVO_FUNCTION_NAMES = {
    0: "Disabled",
    2: "Flap",
    3: "Automatic Flaps",
    4: "Aileron",
    6: "Mount Yaw",
    7: "Mount Pitch",
    8: "Mount Roll",
    9: "Mount Deploy/Retract",
    12: "Mount2 Yaw",
    13: "Mount2 Pitch",
    14: "Mount2 Roll",
    15: "Mount2 Deploy/Retract",
    16: "Differential Spoiler 1",
    17: "Differential Spoiler 2",
    18: "Aileron With Input",
    19: "Elevator",
    20: "Elevator With Input",
    21: "Rudder",
    24: "Flaperon Left",
    25: "Flaperon Right",
    26: "Ground Steering",
    27: "Parachute Release",
    28: "EPM/Gripper",
    29: "Landing Gear",
    30: "Motor Enable Switch",
    41: "Motor Tilt",
    45: "Tilt Motor Rear",
    46: "Tilt Motor Rear Left",
    47: "Tilt Motor Rear Right",
    70: "Throttle",
    73: "Throttle Left",
    74: "Throttle Right",
    75: "Tilt Motor Left",
    76: "Tilt Motor Right",
    77: "Elevon Left",
    78: "Elevon Right",
    79: "V-Tail Left",
    80: "V-Tail Right",
    81: "Boost Engine Throttle",
    88: "Winch",
}
for func, idx in MOTOR_FUNCTION_TO_INDEX.items():
    SERVO_FUNCTION_NAMES[func] = f"Motor {idx + 1}"

class ArdupilotParser:
    """
    Parses an ArduPilot DataFlash .BIN file and exposes the same public API
    as the INAV ``DataParser`` class.
    """

    def __init__(self, log_path, progress_callback=None):
        self.log_path = log_path
        self.progress_callback = progress_callback
        self.firmware_version = "Unknown"
        self.vehicle_type = "Unknown"
        self.mode_table = ARDUPLANE_MODES  # default fallback
        self.ref_lat = None
        self.ref_lon = None
        self.df_merged = None
        self.servo_functions = {} # ch_idx -> function_id (from PARM)
        self.output_mapping = {}
        self.message_counts = {}
        self.is_quadplane = False

        self._parse(log_path)

    # ── Public API (matches DataParser) ──────────────────────────────────

    def get_data(self):
        return self.df_merged

    def get_bounds(self):
        """Returns (min_lat, max_lat, min_lon, max_lon) or None."""
        if self.df_merged is None or 'GPS_coord[0]' not in self.df_merged.columns:
            return None
        return (
            self.df_merged['GPS_coord[0]'].min(),
            self.df_merged['GPS_coord[0]'].max(),
            self.df_merged['GPS_coord[1]'].min(),
            self.df_merged['GPS_coord[1]'].max(),
        )

    def latlon_to_local(self, lat_deg, lon_deg):
        R = 6371000.0
        lat_rad = np.radians(lat_deg)
        lon_rad = np.radians(lon_deg)
        x = R * (lon_rad - self.ref_lon) * np.cos(self.ref_lat)
        y = R * (lat_rad - self.ref_lat)
        return x, y

    # ── Internal parsing ─────────────────────────────────────────────────

    def _parse(self, path):
        if self.progress_callback:
            self.progress_callback("Opening ArduPilot log...", 5)

        # Collect messages into lists
        msgs = {
            'ATT': [], 'GPS': [], 'BAT': [], 'RCIN': [], 'RCOU': [], 'RCO2': [],
            'MODE': [], 'MSG': [], 'STAT': [], 'IMU': [], 'MAG': [],
            'VIBE': [], 'BARO': [], 'QTUN': [], 'POS': [],
            'XKF1': [], 'EV': [], 'CTUN': [], 'ORGN': [], 'HOME': [],
            'TECS': [], 'NTUN': [], 'PM': [], 'GPA': [], 'ERR': [],
            'ATUN': [], 'ATDE': [], 'CAM': [], 'CMD': [], 'D32': [], 'DU32': [],
        }

        if self.progress_callback:
            self.progress_callback("Reading binary log messages...", 10)

        mlog = mavutil.mavlink_connection(path, robust_parsing=True)
        while True:
            m = mlog.recv_match()
            if m is None:
                break
            msg_type = m.get_type()
            self.message_counts[msg_type] = self.message_counts.get(msg_type, 0) + 1
            if msg_type == 'PARM':
                name = getattr(m, 'Name', '')
                if name.startswith('SERVO') and name.endswith('_FUNCTION'):
                    try:
                        # e.g. "SERVO3_FUNCTION"
                        ch_idx_str = name[5:].split('_')[0]
                        ch_idx = int(ch_idx_str)
                        self.servo_functions[ch_idx] = int(getattr(m, 'Value', 0))
                    except (ValueError, IndexError):
                        pass
                elif name == 'Q_ENABLE':
                    if int(getattr(m, 'Value', 0)) == 1:
                        self.is_quadplane = True
                continue

            if msg_type in msgs:
                msgs[msg_type].append(m.to_dict())

        # ── Firmware version & vehicle type ──────────────────────────────
        for msg in msgs['MSG']:
            text = msg.get('Message', '')
            # First MSG is usually "ArduPlane V4.3.2 (hash)" or "ArduCopter V4.5.1 ..."
            for vehicle in VEHICLE_MODE_TABLES:
                if vehicle in text:
                    self.vehicle_type = vehicle
                    self.mode_table = VEHICLE_MODE_TABLES[vehicle]
                    # Extract version string e.g. "ArduPlane V4.3.2 (cafc7b91)"
                    self.firmware_version = text.split('(')[0].strip()
                    break
            if self.vehicle_type != "Unknown":
                break

        if self.progress_callback:
            self.progress_callback("Building data frames...", 30)

        # ── Find Origin/Home (for reference) ─────────────────────────────
        self.origin_lat = None
        self.origin_lon = None
        self.origin_alt = None

        # Prefer ORGN for EKF origin
        if msgs['ORGN']:
            o = msgs['ORGN'][0]
            if o.get('Lat') != 0:
                self.origin_lat = o['Lat'] / 1.0e7
                self.origin_lon = o['Lng'] / 1.0e7
                self.origin_alt = o['Alt'] / 100.0
        elif msgs['HOME']:
            h = msgs['HOME'][0]
            if h.get('Lat') != 0:
                self.origin_lat = h['Lat'] / 1.0e7
                self.origin_lon = h['Lng'] / 1.0e7
                self.origin_alt = h['Alt'] / 100.0

        # ── Convert to DataFrames ────────────────────────────────────────
        df_att = self._to_df(msgs['ATT'])
        df_gps = self._to_df(msgs['GPS'])
        df_bat = self._to_df(msgs['BAT'])
        df_rcin = self._to_df(msgs['RCIN'])
        df_rcou = self._to_df(msgs['RCOU'])
        df_rco2 = self._to_df(msgs['RCO2'])
        df_mode = self._to_df(msgs['MODE'])
        df_stat = self._to_df(msgs['STAT'])
        df_imu = self._to_df(msgs['IMU'])
        df_mag = self._to_df(msgs['MAG'])
        df_vibe = self._to_df(msgs['VIBE'])
        df_baro = self._to_df(msgs['BARO'])
        df_pos = self._to_df(msgs['POS'])
        df_ev = self._to_df(msgs['EV'])
        df_qtun = self._to_df(msgs['QTUN'])
        df_ctun = self._to_df(msgs['CTUN'])
        df_tecs = self._to_df(msgs['TECS'])
        df_ntun = self._to_df(msgs['NTUN'])
        df_pm = self._to_df(msgs['PM'])
        df_gpa = self._to_df(msgs['GPA'])
        df_err = self._to_df(msgs['ERR'])
        df_atun = self._to_df(msgs['ATUN'])
        df_atde = self._to_df(msgs['ATDE'])
        df_cam = self._to_df(msgs['CAM'])
        df_cmd = self._to_df(msgs['CMD'])
        df_d32 = self._to_df(msgs['D32'])
        df_du32 = self._to_df(msgs['DU32'])


        # ── Build the backbone from ATT (highest rate attitude data) ─────
        if df_att.empty:
            raise ValueError("No ATT (attitude) messages found in log — cannot build timeline.")

        # Filter to first IMU instance if multi-IMU
        if 'I' in df_imu.columns and not df_imu.empty:
            df_imu = df_imu[df_imu['I'] == 0].copy()
        if 'I' in df_gps.columns and not df_gps.empty:
            df_gps = df_gps[df_gps['I'] == 0].copy()
        if 'I' in df_mag.columns and not df_mag.empty:
            df_mag = df_mag[df_mag['I'] == 0].copy()
        if 'I' in df_gpa.columns and not df_gpa.empty:
            df_gpa = df_gpa[df_gpa['I'] == 0].copy()

        if self.progress_callback:
            self.progress_callback("Merging messages by timestamp...", 50)

        # Use ATT as the backbone timebase
        backbone = df_att[['TimeUS']].copy()
        backbone = backbone.sort_values('TimeUS').drop_duplicates(subset='TimeUS').reset_index(drop=True)

        # Helper to merge another DF onto the backbone
        def merge_onto(backbone, other, columns, prefix='', direction='nearest'):
            if other.empty:
                return backbone
            other = other.sort_values('TimeUS').drop_duplicates(subset='TimeUS')
            selected_cols = []
            for c in columns:
                if c not in other.columns:
                    continue
                target_name = f"{prefix}{c}" if prefix else c
                if target_name not in backbone.columns:
                    selected_cols.append(c)
            cols_to_use = ['TimeUS'] + selected_cols
            if len(cols_to_use) == 1:
                return backbone
            sub = other[cols_to_use].copy()
            if prefix:
                rename = {c: f"{prefix}{c}" for c in cols_to_use if c != 'TimeUS'}
                sub = sub.rename(columns=rename)
            merged = pd.merge_asof(backbone, sub, on='TimeUS', direction=direction)
            return merged

        # Attitude
        backbone = merge_onto(backbone, df_att, [
            'Roll', 'Pitch', 'Yaw', 'DesRoll', 'DesPitch', 'DesYaw', 'ErrRP', 'ErrYaw', 'AEKF'
        ])

        # GPS
        gps_cols = ['Lat', 'Lng', 'Alt', 'RelAlt', 'Spd', 'GCrs', 'NSats', 'HDop', 'Status', 'VZ', 'GMS', 'GWk']
        backbone = merge_onto(backbone, df_gps, gps_cols)

        # Battery
        bat_cols = ['Volt', 'Curr', 'CurrTot', 'Temp', 'RemPct']
        backbone = merge_onto(backbone, df_bat, bat_cols)

        # RC Inputs
        rcin_cols = [f'C{i}' for i in range(1, 17)]
        backbone = merge_onto(backbone, df_rcin, rcin_cols, prefix='rcin_')

        # RC Outputs
        rcou_cols = [f'C{i}' for i in range(1, 33)]
        backbone = merge_onto(backbone, df_rcou, rcou_cols, prefix='rcou_')
        backbone = merge_onto(backbone, df_rco2, rcou_cols, prefix='rcou_')

        # Baro altitude
        if not df_baro.empty and 'Alt' in df_baro.columns:
            # Rename to avoid collision with GPS Alt
            df_baro_sub = df_baro[['TimeUS', 'Alt']].copy()
            df_baro_sub = df_baro_sub.rename(columns={'Alt': 'BaroAlt'})
            df_baro_sub = df_baro_sub.sort_values('TimeUS').drop_duplicates(subset='TimeUS')
            backbone = pd.merge_asof(backbone, df_baro_sub, on='TimeUS', direction='nearest')

        # IMU (gyro + accel)
        imu_cols = ['GyrX', 'GyrY', 'GyrZ', 'AccX', 'AccY', 'AccZ', 'T']
        backbone = merge_onto(backbone, df_imu, imu_cols)

        # Magnetometer
        mag_cols = ['MagX', 'MagY', 'MagZ', 'OfsX', 'OfsY', 'OfsZ', 'MOX', 'MOY', 'MOZ', 'Health']
        backbone = merge_onto(backbone, df_mag, mag_cols)

        # Vibration
        vibe_cols = ['VibeX', 'VibeY', 'VibeZ']
        backbone = merge_onto(backbone, df_vibe, vibe_cols)

        # POS (EKF-derived position)
        pos_cols = ['Lat', 'Lng', 'Alt', 'RelHomeAlt', 'RelOriginAlt']
        if not df_pos.empty:
            df_pos_sub = df_pos[['TimeUS'] + [c for c in pos_cols if c in df_pos.columns]].copy()
            # Rename to avoid collision with GPS
            rename_map = {'Lat': 'POS_Lat', 'Lng': 'POS_Lng', 'Alt': 'POS_Alt',
                          'RelHomeAlt': 'POS_RelHomeAlt', 'RelOriginAlt': 'POS_RelOriginAlt'}
            df_pos_sub = df_pos_sub.rename(columns={k: v for k, v in rename_map.items() if k in df_pos_sub.columns})
            df_pos_sub = df_pos_sub.sort_values('TimeUS').drop_duplicates(subset='TimeUS')
            backbone = pd.merge_asof(backbone, df_pos_sub, on='TimeUS', direction='nearest')

        # STAT (armed/flying)
        stat_cols = ['isFlying', 'Armed']
        backbone = merge_onto(backbone, df_stat, stat_cols)

        # Tuning (Throttle Out, etc)
        if not df_ctun.empty:
            backbone = merge_onto(backbone, df_ctun, [
                'ThI', 'ABst', 'ThO', 'ThH', 'DAlt', 'Alt', 'BAlt', 'SAlt', 'TAlt',
                'DCRt', 'CRt', 'N', 'ThD', 'As', 'AsT', 'SAs', 'E2T', 'GU',
                'NavRoll', 'NavPitch', 'Roll', 'Pitch', 'RdrOut', 'RdO'
            ], prefix='CTUN_')
        if not df_qtun.empty:
            backbone = merge_onto(backbone, df_qtun, ['ThO', 'DAlt', 'Alt', 'CRt'], prefix='QTUN_')
        if not df_tecs.empty:
            backbone = merge_onto(backbone, df_tecs, ['h', 'h_dem', 'v', 'v_dem', 'thr', 'ptch'], prefix='TECS_')
        if not df_ntun.empty:
            backbone = merge_onto(backbone, df_ntun, [
                'WPDst', 'WPBrg', 'PErX', 'PErY', 'DVelX', 'DVelY', 'VelX', 'VelY',
                'DAcX', 'DAcY', 'DRol', 'DPit', 'Dist', 'TBrg', 'NavBrg', 'AltE',
                'XT', 'XTi', 'TLat', 'TLng', 'TAsp', 'AsE'
            ], prefix='NTUN_')
        if not df_gpa.empty:
            backbone = merge_onto(backbone, df_gpa, ['VDop', 'HAcc', 'VAcc', 'SAcc', 'VV', 'SMS', 'Delta', 'YAcc'], prefix='GPA_')
        if not df_pm.empty:
            backbone = merge_onto(backbone, df_pm, ['NLon', 'NLoop', 'NL', 'MaxT', 'Mem', 'Load', 'ErrL', 'ErrC', 'ErC', 'IntE', 'InE', 'SPIC', 'I2CC', 'I2CI'], prefix='PM_')
        if not df_atun.empty:
            backbone = merge_onto(backbone, df_atun, ['Axis', 'TuneStep', 'RateMin', 'RateMax', 'RPGain', 'RDGain', 'SPGain'], prefix='ATUN_', direction='backward')
        if not df_atde.empty:
            backbone = merge_onto(backbone, df_atde, ['Angle', 'Rate'], prefix='ATDE_', direction='backward')
        if not df_cam.empty:
            backbone = merge_onto(backbone, df_cam, ['GPSTime', 'Lat', 'Lng', 'Alt', 'Roll', 'Pitch', 'Yaw'], prefix='CAM_', direction='backward')
        if not df_cmd.empty:
            backbone = merge_onto(backbone, df_cmd, ['CTot', 'CNum', 'CId', 'Copt', 'Prm1', 'Prm2', 'Prm3', 'Prm4', 'Alt', 'Lat', 'Lng', 'Frame'], prefix='CMD_', direction='backward')
        if not df_err.empty:
            backbone = merge_onto(backbone, df_err, ['Subsys', 'ECode'], prefix='ERR_', direction='backward')
        if not df_d32.empty:
            backbone = merge_onto(backbone, df_d32, ['Id', 'id', 'Value', 'value'], prefix='D32_', direction='backward')
        if not df_du32.empty:
            backbone = merge_onto(backbone, df_du32, ['Id', 'id', 'Value', 'value'], prefix='DU32_', direction='backward')

        # MODE — build a continuous mode column from sparse mode-change events
        if not df_mode.empty:
            df_mode_sorted = df_mode[['TimeUS', 'Mode', 'ModeNum']].sort_values('TimeUS')
            backbone = pd.merge_asof(backbone, df_mode_sorted, on='TimeUS', direction='backward')
        else:
            backbone['Mode'] = 0
            backbone['ModeNum'] = 0

        # Events
        if not df_ev.empty:
            df_ev_sorted = df_ev[['TimeUS', 'Id']].sort_values('TimeUS')
            df_ev_sorted = df_ev_sorted.rename(columns={'Id': 'EventId'})
            backbone = pd.merge_asof(backbone, df_ev_sorted, on='TimeUS', direction='backward')

        if self.progress_callback:
            self.progress_callback("Normalizing column names...", 70)

        # ── Normalize column names to match INAV schema ──────────────────
        rename = {
            'TimeUS': 'time (us)',
            # Attitude (ArduPilot reports in degrees already, no deci-deg conversion)
            'Roll': 'attitude[0]',
            'Pitch': 'attitude[1]',
            'Yaw': 'attitude[2]',
            'DesRoll': 'Desired Roll',
            'DesPitch': 'Desired Pitch',
            'DesYaw': 'Desired Yaw',
            'ErrRP': 'Attitude Err Roll/Pitch',
            'ErrYaw': 'Attitude Err Yaw',
            'AEKF': 'Attitude EKF Active',
            # GPS
            'Lat': 'GPS_coord[0]',
            'Lng': 'GPS_coord[1]',
            'Alt': 'GPS_altitude',
            'RelAlt': 'GPS_rel_altitude',
            'Spd': 'GPS_speed (m/s)',
            'GCrs': 'GPS_ground_course',
            'NSats': 'GPS_numSat',
            'HDop': 'GPS_hdop',
            'Status': 'GPS_fixType',
            'VZ': 'GPS_VZ',
            'GMS': 'GPS_time_ms',
            'GWk': 'GPS_week',
            # Battery
            'Volt': 'vbat (V)',
            'Curr': 'amperage (A)',
            'CurrTot': 'energyCumulative (mAh)',
            'RemPct': 'batteryRemaining',
            # IMU
            'GyrX': 'gyroADC[0]',
            'GyrY': 'gyroADC[1]',
            'GyrZ': 'gyroADC[2]',
            'AccX': 'accSmooth[0]',
            'AccY': 'accSmooth[1]',
            'AccZ': 'accSmooth[2]',
            'T': 'IMUTemperature',
            # Mag
            'MagX': 'magADC[0]',
            'MagY': 'magADC[1]',
            'MagZ': 'magADC[2]',
            'OfsX': 'Mag Offset X',
            'OfsY': 'Mag Offset Y',
            'OfsZ': 'Mag Offset Z',
            'MOX': 'Mag Motor Offset X',
            'MOY': 'Mag Motor Offset Y',
            'MOZ': 'Mag Motor Offset Z',
            'Health': 'Mag Health',
            # Vibe
            'VibeX': 'vibeX',
            'VibeY': 'vibeY',
            'VibeZ': 'vibeZ',
            # Baro
            'BaroAlt': 'BaroAlt (cm)',  # Note: ArduPilot BaroAlt is already in meters, we'll convert below
            # Tuning Setpoints
            'CTUN_DAlt': 'Desired Altitude (Copter)',
            'QTUN_DAlt': 'Desired Altitude (Quad)',
            'TECS_thr': 'Throttle (Commanded)',
            'CTUN_ThO': 'Throttle Out (Copter)',
            'QTUN_ThO': 'Throttle Out (Quad)',
            'CTUN_ThI': 'Throttle In (Copter)',
            'CTUN_ThH': 'Throttle Hover (Copter)',
            'CTUN_ThD': 'Throttle Desired (Copter)',
            'CTUN_Alt': 'Control Altitude (Copter)',
            'CTUN_BAlt': 'Baro Altitude (Copter)',
            'CTUN_SAlt': 'Sonar Altitude (Copter)',
            'CTUN_TAlt': 'Terrain Altitude (Copter)',
            'CTUN_DCRt': 'Desired Climb Rate (Copter)',
            'CTUN_CRt': 'Climb Rate (Copter)',
            'CTUN_N': 'Harmonic Notch Freq',
            'NTUN_WPDst': 'WP Distance',
            'NTUN_Dist': 'WP Distance',
            'NTUN_WPBrg': 'WP Bearing',
            'NTUN_TBrg': 'WP Bearing',
            'NTUN_NavBrg': 'Nav Bearing',
            'NTUN_AltE': 'Altitude Error',
            'NTUN_XT': 'Cross Track Error',
            'NTUN_XTi': 'Cross Track Integral',
            'NTUN_TAsp': 'Target Airspeed',
            'NTUN_PErX': 'Position Error X',
            'NTUN_PErY': 'Position Error Y',
            'NTUN_DVelX': 'Desired Velocity X',
            'NTUN_DVelY': 'Desired Velocity Y',
            'NTUN_VelX': 'Velocity X',
            'NTUN_VelY': 'Velocity Y',
            'NTUN_DAcX': 'Desired Accel X',
            'NTUN_DAcY': 'Desired Accel Y',
            'NTUN_DRol': 'Desired Roll Nav',
            'NTUN_DPit': 'Desired Pitch Nav',
            'GPA_VDop': 'GPS VDOP',
            'GPA_HAcc': 'GPS Horizontal Accuracy',
            'GPA_VAcc': 'GPS Vertical Accuracy',
            'GPA_SAcc': 'GPS Speed Accuracy',
            'GPA_VV': 'GPS Vertical Velocity Valid',
            'GPA_SMS': 'GPS Sample Time',
            'GPA_Delta': 'GPS Delta Time',
            'PM_NLon': 'PM Long Loops',
            'PM_NLoop': 'PM Loop Count',
            'PM_NL': 'PM Loop Count',
            'PM_MaxT': 'PM Max Loop Time',
            'PM_Mem': 'PM Free Memory',
            'PM_Load': 'PM CPU Load',
            'ERR_Subsys': 'Error Subsystem',
            'ERR_ECode': 'Error Code',
            'ATUN_Axis': 'AutoTune Axis',
            'ATUN_TuneStep': 'AutoTune Step',
            'ATUN_RateMin': 'AutoTune Rate Min',
            'ATUN_RateMax': 'AutoTune Rate Max',
            'ATUN_RPGain': 'AutoTune RP Gain',
            'ATUN_RDGain': 'AutoTune RD Gain',
            'ATUN_SPGain': 'AutoTune SP Gain',
            'ATDE_Angle': 'AutoTune Angle',
            'ATDE_Rate': 'AutoTune Rate',
            'D32_id': 'D32_Id',
            'D32_value': 'D32_Value',
            'DU32_id': 'DU32_Id',
            'DU32_value': 'DU32_Value',
            # TECS (Fixed Wing)
            'TECS_h': 'TECS Altitude',
            'TECS_h_dem': 'TECS Desired Alt',
            'TECS_v': 'TECS Airspeed',
            'TECS_v_dem': 'TECS Desired Airspeed',
            'TECS_ptch': 'TECS Desired Pitch',
        }

        # RC Inputs → rcData[0..3]
        # ArduPilot default is often AETR: 1:Roll, 2:Pitch, 3:Throttle, 4:Yaw
        # Internal schema expects: 0:Roll, 1:Pitch, 2:Yaw, 3:Throttle
        mapping = {
            'rcin_C1': 'rcData[0]',
            'rcin_C2': 'rcData[1]',
            'rcin_C3': 'rcData[3]', # Throttle
            'rcin_C4': 'rcData[2]', # Yaw
        }
        for src, dst in mapping.items():
            if src in backbone.columns:
                rename[src] = dst

        # Extra RC inputs
        for i in range(5, 17):
            src = f'rcin_C{i}'
            dst = f'rcData[{i-1}]'
            if src in backbone.columns:
                rename[src] = dst

        # RC Outputs -> motor[0..31] and servo[0..31]
        # Dynamic mapping based on SERVO_FUNCTION parameters if available
        self.output_mapping = {}

        def add_output_mapping(src, dst, channel, func, role, note=""):
            rename[src] = dst
            self.output_mapping[dst] = {
                "source": src,
                "channel": channel,
                "function_id": func,
                "function_name": SERVO_FUNCTION_NAMES.get(func, f"Function {func}") if func is not None else "Default mapping",
                "role": role,
                "note": note,
            }

        if self.servo_functions:
            mapped_rcou = set()

            def next_free_motor(preferred, used):
                if preferred not in used:
                    return preferred
                for candidate in range(32):
                    if candidate not in used:
                        return candidate
                return None

            used_motor_indices = set()

            # First map numbered ArduPilot motor functions to their real motor number.
            for i in range(1, 33):
                src = f'rcou_C{i}'
                if src not in backbone.columns:
                    continue
                func = self.servo_functions.get(i, 0)
                if func in MOTOR_FUNCTION_TO_INDEX:
                    motor_idx = MOTOR_FUNCTION_TO_INDEX[func]
                    add_output_mapping(
                        src, f'motor[{motor_idx}]', i, func, "motor",
                        "Numbered ArduPilot motor function mapped to its motor number."
                    )
                    used_motor_indices.add(motor_idx)
                    mapped_rcou.add(src)

            # Then map throttle-style functions. These do not have a numbered motor
            # identity, so use their conventional slot unless it is already occupied.
            for i in range(1, 33):
                src = f'rcou_C{i}'
                if src not in backbone.columns or src in mapped_rcou:
                    continue
                func = self.servo_functions.get(i, 0)
                if func in THROTTLE_FUNCTIONS:
                    motor_idx = next_free_motor(THROTTLE_FUNCTIONS[func], used_motor_indices)
                    if motor_idx is not None:
                        add_output_mapping(
                            src, f'motor[{motor_idx}]', i, func, "motor",
                            "Throttle-style function mapped to the first available motor slot."
                        )
                        used_motor_indices.add(motor_idx)
                        mapped_rcou.add(src)

            # Servo/control-surface outputs keep their physical output channel index.
            for i in range(1, 33):
                src = f'rcou_C{i}'
                if src not in backbone.columns or src in mapped_rcou:
                    continue
                func = self.servo_functions.get(i, 0)
                if func in SERVO_FUNCTIONS:
                    add_output_mapping(
                        src, f'servo[{i-1}]', i, func, "servo",
                        "Servo/control-surface function kept on its physical output channel."
                    )
                    mapped_rcou.add(src)

            # Map any remaining unmapped active channels as generic servos
            for i in range(1, 33):
                src = f'rcou_C{i}'
                if src in backbone.columns and src not in mapped_rcou:
                    # Only map if it actually moves or is a low channel
                    if i <= 4 or backbone[src].max() != backbone[src].min():
                        func = self.servo_functions.get(i, 0)
                        add_output_mapping(
                            src, f'servo[{i-1}]', i, func, "servo",
                            "Unclassified active output kept as a generic servo on its physical channel."
                        )
        
        elif self.vehicle_type == "ArduPlane":
            # Fallback: ArduPilot plane defaults are 1:Ail, 2:Ele, 3:Rud, 4:Thr.
            out_mapping = {
                'rcou_C1': 'servo[0]',  # Aileron
                'rcou_C2': 'servo[1]',  # Elevator
                'rcou_C3': 'servo[2]',  # Rudder
                'rcou_C4': 'motor[0]',  # Throttle
            }
            for src, dst in out_mapping.items():
                if src in backbone.columns:
                    channel = int(src.split('_C')[1])
                    role = "motor" if dst.startswith("motor[") else "servo"
                    add_output_mapping(src, dst, channel, None, role, "Fallback ArduPlane default output mapping.")
            # Remaining outputs
            for i in range(5, 33):
                src = f'rcou_C{i}'
                dst = f'servo[{i-1}]'
                if src in backbone.columns:
                    add_output_mapping(src, dst, i, None, "servo", "Fallback generic servo output.")
        else:
            # Fallback Default/Copter: map 1-to-1
            for i in range(1, 13):
                src = f'rcou_C{i}'
                dst = f'motor[{i-1}]'
                if src in backbone.columns:
                    add_output_mapping(src, dst, i, None, "motor", "Fallback motor output mapping.")
            # Rest as servos
            for i in range(13, 33):
                src = f'rcou_C{i}'
                dst = f'servo[{i-1}]'
                if src in backbone.columns:
                    add_output_mapping(src, dst, i, None, "servo", "Fallback generic servo output.")


        backbone = backbone.rename(columns=rename)
        if backbone.columns.has_duplicates:
            deduped = pd.DataFrame(index=backbone.index)
            for col in dict.fromkeys(backbone.columns):
                values = backbone.loc[:, col]
                if isinstance(values, pd.DataFrame):
                    deduped[col] = values.bfill(axis=1).iloc[:, 0]
                else:
                    deduped[col] = values
            backbone = deduped

        # ── Forward-fill and clean up NaN ────────────────────────────────
        # Do this BEFORE deriving mode names so ModeNum gets back-filled
        backbone = backbone.ffill().bfill()

        # ── Derive mode name string column ───────────────────────────────
        if 'ModeNum' in backbone.columns:
            backbone['flightModeFlags (flags)'] = backbone['ModeNum'].apply(
                lambda m: self.mode_table.get(int(m), f"MODE_{int(m)}") if pd.notna(m) else "UNKNOWN"
            )
        else:
            backbone['flightModeFlags (flags)'] = "UNKNOWN"

        # ── Derive simple ArduPilot state flags for the flag viewer ─────
        def as_bool(value):
            if pd.isna(value):
                return False
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "armed", "flying", "yes"}
            return bool(value)

        def state_flags(row):
            flags = []
            if 'Armed' in row.index:
                flags.append("ARMED" if as_bool(row['Armed']) else "DISARMED")
            if 'isFlying' in row.index:
                flags.append("FLYING" if as_bool(row['isFlying']) else "ON_GROUND")
            return "|".join(flags)

        if 'Armed' in backbone.columns or 'isFlying' in backbone.columns:
            backbone['stateFlags (flags)'] = backbone.apply(state_flags, axis=1)
        else:
            backbone['stateFlags (flags)'] = ""

        # ── Baro altitude: ArduPilot reports in meters, INAV schema uses cm
        if 'BaroAlt (cm)' in backbone.columns:
            backbone['BaroAlt (cm)'] = backbone['BaroAlt (cm)'] * 100.0
            
        # ── GPS Coordinates: ArduPilot binary logs store Lat/Lng as integers (units 1e-7 deg)
        #    If values are very large, we must normalize them to standard degrees.
        for col in ['GPS_coord[0]', 'GPS_coord[1]', 'POS_Lat', 'POS_Lng', 'CAM_Lat', 'CAM_Lng', 'CMD_Lat', 'CMD_Lng']:
            if col in backbone.columns:
                # If values are consistently above 1000, they are definitely in 1e-7 format
                if backbone[col].abs().max() > 1000:
                    backbone[col] = backbone[col] / 1.0e7

        # ── AccSmooth: ArduPilot reports accel in m/s² (not raw ADC like INAV).
        #    The INAV stats code divides by 2048 to get G.
        #    For ArduPilot, 1G ≈ 9.81 m/s², so we scale to match INAV's 2048 LSB/G convention.
        for col in ['accSmooth[0]', 'accSmooth[1]', 'accSmooth[2]']:
            if col in backbone.columns:
                backbone[col] = backbone[col] * (2048.0 / 9.81)

        backbone = backbone.drop_duplicates(subset='time (us)')
        backbone = backbone.sort_values('time (us)').reset_index(drop=True)

        if self.progress_callback:
            self.progress_callback("Calculating local coordinates...", 80)

        # ── Calculate local XY coordinates ───────────────────────────────
        if 'GPS_coord[0]' in backbone.columns and 'GPS_coord[1]' in backbone.columns:
            self._calculate_local_coordinates(backbone)
        else:
            backbone['pos_x'] = 0.0
            backbone['pos_y'] = 0.0
            backbone['pos_z'] = 0.0

        self.df_merged = backbone
        if self.progress_callback:
            self.progress_callback("ArduPilot log loaded.", 90)

    # ── Coordinate conversion (matches DataParser logic) ─────────────────

    def _calculate_local_coordinates(self, df):
        R = 6371000.0

        # Filter out invalid (0,0) coordinates
        # Also ignore points where NSats is low or HDOP is high (likely search phase / bad lock)
        valid_gps_mask = (df['GPS_coord[0]'] != 0) & (df['GPS_coord[1]'] != 0)
        if 'GPS_numSat' in df.columns:
            valid_gps_mask &= (df['GPS_numSat'] >= 8)
        if 'GPS_hdop' in df.columns:
            valid_gps_mask &= (df['GPS_hdop'] <= 2.0)
        
        # If no valid GPS, just center at 0,0
        if not valid_gps_mask.any():
            df['pos_x'], df['pos_y'], df['pos_z'] = 0.0, 0.0, 0.0
            return

        lat_all = np.radians(df['GPS_coord[0]'])
        lon_all = np.radians(df['GPS_coord[1]'])

        if 'POS_RelHomeAlt' in df.columns:
            alt_all = df['POS_RelHomeAlt']
        elif 'GPS_altitude' in df.columns:
            alt_all = df['GPS_altitude']
        else:
            alt_all = pd.Series(0.0, index=df.index)

        # Determine robust reference point
        # Instead of relying on ORGN/HOME (which can be set incorrectly during a bad initial lock),
        # or the first 10 points (which could be the bad initial lock),
        # we take the MEDIAN of all valid GPS points in the log.
        # This perfectly centers the flight and is immune to isolated jumps at the start/end.
        valid_lats = lat_all[valid_gps_mask]
        valid_lons = lon_all[valid_gps_mask]
        
        self.ref_lat = valid_lats.median()
        self.ref_lon = valid_lons.median()
        
        # For altitude, we still want a baseline near the start of the valid flight
        valid_alts = alt_all[valid_gps_mask]
        ref_alt = valid_alts.iloc[:10].mean() if not valid_alts.iloc[:10].isna().all() else 0.0

        # Calculate raw X/Y/Z relative to median center
        df['pos_x'] = R * (lon_all - self.ref_lon) * np.cos(self.ref_lat)
        df['pos_y'] = R * (lat_all - self.ref_lat)
        df['pos_z'] = alt_all - ref_alt
        
        # Filter out extreme outliers (e.g. > 100km from the median center) 
        # Since we use the median, the actual flight is guaranteed to be near 0,0.
        # Anything 100km away is definitely a glitch.
        dist_sq = df['pos_x']**2 + df['pos_y']**2
        outlier_mask = dist_sq > (100000**2) 
        
        # Mask bad points in both local coordinates and original GPS coords (for map bounds)
        bad_mask = (~valid_gps_mask) | outlier_mask
        
        df.loc[bad_mask, ['pos_x', 'pos_y', 'pos_z']] = np.nan
        df.loc[bad_mask, ['GPS_coord[0]', 'GPS_coord[1]']] = np.nan
        
        # We ffill/bfill to provide a continuous path, but we must NOT fill GPS_coord with 0.0
        # as that ruins the bounding box (min/max) for map fetching.
        # pos_x/y/z can be 0.0 as they are relative to the ref point.
        df[['pos_x', 'pos_y', 'pos_z']] = df[['pos_x', 'pos_y', 'pos_z']].ffill().bfill().fillna(0.0)
        df[['GPS_coord[0]', 'GPS_coord[1]']] = df[['GPS_coord[0]', 'GPS_coord[1]']].ffill().bfill()
        
        # If the entire log has no GPS, ffill/bfill will still be NaN. 
        # In that case, we can use the ref_lat/lon as a fallback for the bounds.
        if df['GPS_coord[0]'].isna().all():
            df['GPS_coord[0]'] = np.degrees(self.ref_lat) if self.ref_lat is not None else 0.0
            df['GPS_coord[1]'] = np.degrees(self.ref_lon) if self.ref_lon is not None else 0.0

        # Smooth GPS noise
        window = max(10, len(df) // 500)
        for col in ['pos_x', 'pos_y', 'pos_z']:
            df[col] = df[col].rolling(window=window, min_periods=1, center=True).mean()

        df[['pos_x', 'pos_y', 'pos_z']] = df[['pos_x', 'pos_y', 'pos_z']].ffill().bfill().fillna(0.0)

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _to_df(msg_list):
        """Convert a list of message dicts to a DataFrame, dropping the type tag."""
        if not msg_list:
            return pd.DataFrame()
        df = pd.DataFrame(msg_list)
        if 'mavpackettype' in df.columns:
            df = df.drop(columns=['mavpackettype'])
        return df
