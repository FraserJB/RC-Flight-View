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
ArduPilot-specific flag and mode definitions for the Flag Viewer.

Provides the same structure as the INAV definitions in flag_viewer.py,
so the FlagViewer can display ArduPilot status data seamlessly.
"""

# ── ArduPlane Flight Modes ──────────────────────────────────────────────
ARDUPLANE_MODE_MAP = {
    0: "MANUAL", 1: "CIRCLE", 2: "STABILIZE", 3: "TRAINING",
    4: "ACRO", 5: "FLY_BY_WIRE_A", 6: "FLY_BY_WIRE_B", 7: "CRUISE",
    8: "AUTOTUNE", 10: "AUTO", 11: "RTL", 12: "LOITER",
    13: "TAKEOFF", 14: "AVOID_ADSB", 15: "GUIDED",
    17: "QSTABILIZE", 18: "QHOVER", 19: "QLOITER",
    20: "QLAND", 21: "QRTL", 22: "QAUTOTUNE", 23: "QACRO",
    24: "THERMAL", 25: "LOITER_ALT_QLAND",
}
ARDUPLANE_MODE_NAMES = list(ARDUPLANE_MODE_MAP.values())

# ── ArduCopter Flight Modes ────────────────────────────────────────────
ARDUCOPTER_MODE_MAP = {
    0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
    9: "LAND", 11: "DRIFT", 13: "SPORT", 14: "FLIP",
    15: "AUTOTUNE", 16: "POSHOLD", 17: "BRAKE", 18: "THROW",
    19: "AVOID_ADSB", 20: "GUIDED_NOGPS", 21: "SMART_RTL",
    22: "FLOWHOLD", 23: "FOLLOW", 24: "ZIGZAG", 25: "SYSTEMID",
    26: "AUTOROTATE", 27: "AUTO_RTL",
}
ARDUCOPTER_MODE_NAMES = list(ARDUCOPTER_MODE_MAP.values())

ARDUROVER_MODE_MAP = {
    0: "MANUAL", 1: "ACRO", 3: "STEERING", 4: "HOLD",
    5: "LOITER", 6: "FOLLOW", 7: "SIMPLE",
    10: "AUTO", 11: "RTL", 12: "SMART_RTL", 15: "GUIDED",
}
ARDUROVER_MODE_NAMES = list(ARDUROVER_MODE_MAP.values())

# ── Combined unique modes for "All ArduPilot" ──────────────────────────
ALL_ARDUPILOT_MODE_NAMES = sorted(set(ARDUPLANE_MODE_NAMES + ARDUCOPTER_MODE_NAMES))

# ── ArduPilot state flags (derived from STAT message) ──────────────────
ARDUPILOT_STATE_FLAGS = [
    "ARMED", "DISARMED", "FLYING", "ON_GROUND",
]

# ── ArduPilot GPS Fix Types ─────────────────────────────────────────────
ARDUPILOT_GPS_FIX = {
    0: "NO_GPS", 1: "NO_FIX", 2: "2D_FIX", 3: "3D_FIX",
    4: "DGPS", 5: "RTK_FLOAT", 6: "RTK_FIXED",
}

ARDUPILOT_BOOLEAN_VALID = {
    0: "INVALID",
    1: "VALID",
}

ARDUPILOT_EKF_ACTIVE = {
    0: "EKF_INACTIVE",
    1: "EKF1",
    2: "EKF2",
    3: "EKF3",
}

# ── ArduPilot Event IDs (common ones) ──────────────────────────────────
ARDUPILOT_EVENTS = {
    10: "ARMED",
    11: "DISARMED",
    15: "AUTO_ARMED",
    17: "LAND_COMPLETE_MAYBE",
    18: "LAND_COMPLETE",
    19: "LOST_GPS",
    21: "FLIP_START",
    22: "FLIP_END",
    25: "SET_HOME",
    26: "SET_SIMPLE_ON",
    27: "SET_SIMPLE_OFF",
    28: "NOT_LANDED",
    29: "SET_SUPERSIMPLE_ON",
    30: "AUTOTUNE_INITIALISED",
    31: "AUTOTUNE_OFF",
    32: "AUTOTUNE_RESTART",
    33: "AUTOTUNE_SUCCESS",
    34: "AUTOTUNE_FAILED",
    35: "AUTOTUNE_REACHED_LIMIT",
    36: "AUTOTUNE_PILOT_TESTING",
    37: "AUTOTUNE_SAVEDGAINS",
    38: "SAVE_TRIM",
    39: "SAVEWP_ADD_WP",
    41: "FENCE_ENABLE",
    42: "FENCE_DISABLE",
    43: "ACRO_TRAINER_OFF",
    44: "ACRO_TRAINER_LEVELING",
    45: "ACRO_TRAINER_LIMITED",
    46: "GRIPPER_GRAB",
    47: "GRIPPER_RELEASE",
    49: "PARACHUTE_DISABLED",
    50: "PARACHUTE_ENABLED",
    51: "PARACHUTE_RELEASED",
    52: "LANDING_GEAR_DEPLOYED",
    53: "LANDING_GEAR_RETRACTED",
    54: "MOTORS_EMERGENCY_STOPPED",
    55: "MOTORS_EMERGENCY_STOP_CLEARED",
    56: "MOTORS_INTERLOCK_DISABLED",
    57: "MOTORS_INTERLOCK_ENABLED",
    58: "ROTOR_RUNUP_COMPLETE",
    59: "ROTOR_SPEED_BELOW_CRITICAL",
    60: "EKF_ALT_RESET",
    61: "LAND_CANCELLED_BY_PILOT",
    62: "EKF_YAW_RESET",
    63: "AVOIDANCE_ADSB_ENABLE",
    64: "AVOIDANCE_ADSB_DISABLE",
    65: "AVOIDANCE_PROXIMITY_ENABLE",
    66: "AVOIDANCE_PROXIMITY_DISABLE",
    67: "GPS_PRIMARY_CHANGED",
    71: "ZIGZAG_STORE_A",
    72: "ZIGZAG_STORE_B",
    73: "LAND_REPO_ACTIVE",
    74: "STANDBY_ENABLE",
    75: "STANDBY_DISABLE",
    76: "FENCE_ALT_MAX_ENABLE",
    77: "FENCE_ALT_MAX_DISABLE",
    78: "FENCE_CIRCLE_ENABLE",
    79: "FENCE_CIRCLE_DISABLE",
    80: "FENCE_ALT_MIN_ENABLE",
    81: "FENCE_ALT_MIN_DISABLE",
    82: "FENCE_POLYGON_ENABLE",
    83: "FENCE_POLYGON_DISABLE",
    85: "EK3_SOURCES_SET_TO_PRIMARY",
    86: "EK3_SOURCES_SET_TO_SECONDARY",
    87: "EK3_SOURCES_SET_TO_TERTIARY",
    90: "AIRSPEED_PRIMARY_CHANGED",
    163: "SURFACED",
    164: "NOT_SURFACED",
    165: "BOTTOMED",
    166: "NOT_BOTTOMED",
}


def get_ardupilot_flag_params(vehicle_type="ArduPlane"):
    """
    Returns a FLAG_PARAMS dict for ArduPilot, in the same format
    used by flag_viewer.get_flag_params() for INAV.
    
    The returned dict maps column names → (kind, definition).
    """
    if "Copter" in vehicle_type:
        mode_map = ARDUCOPTER_MODE_MAP
        mode_names = ARDUCOPTER_MODE_NAMES
    elif "Rover" in vehicle_type or "rover" in vehicle_type:
        mode_map = ARDUROVER_MODE_MAP
        mode_names = ARDUROVER_MODE_NAMES
    else:
        mode_map = ARDUPLANE_MODE_MAP
        mode_names = ARDUPLANE_MODE_NAMES

    return {
        "flightModeFlags (flags)":  ("text", mode_names),
        "stateFlags (flags)":       ("text", ARDUPILOT_STATE_FLAGS),
        "GPS_fixType":              ("enum", ARDUPILOT_GPS_FIX),
        "EventId":                  ("enum", ARDUPILOT_EVENTS),
        "GPS Vertical Velocity Valid": ("enum", ARDUPILOT_BOOLEAN_VALID),
        "Attitude EKF Active":      ("enum", ARDUPILOT_EKF_ACTIVE),
    }
