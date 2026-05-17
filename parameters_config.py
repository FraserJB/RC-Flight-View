# Copyright (C) 2026 Fraser Boyd
#
# Comprehensive parameter definitions for INAV and ArduPilot DataFlash logs.

ENCODED_PARAMS = {
    "navState": {
        0: "IDLE", 1: "RTH_START", 2: "RTH_ENROUTE", 3: "RTH_APPROACH", 
        4: "RTH_LANDING", 5: "RTH_FINISH", 6: "RTH_DONE", 
        7: "POSHOLD", 8: "CRUISE", 9: "WP_ENROUTE", 10: "WP_DONE",
        11: "LAUNCH", 12: "LANDING", 13: "EMERG_LANDING",
        14: "COURSE_HOLD", 15: "CRUISE_2D",
        26: "LAUNCH_IDLE", 27: "LAUNCH_MOTOR_WAIT", 28: "LAUNCH_IN_PROGRESS"
    },
    "GPS_fixType": {
        0: "No Fix", 1: "Dead Reckoning", 2: "2D Fix", 3: "3D Fix", 4: "GNSS+Dead Reckoning", 5: "Time Only"
    },
    "failsafePhase (flags)": {
        0: "IDLE", 1: "RX_LOSS_DETECTED", 2: "LANDING", 3: "LANDED", 4: "RX_LOSS_MONITORING", 5: "RX_LOSS_RECOVERED"
    }
}

ARDUPILOT_ENCODED_PARAMS = {
    **ENCODED_PARAMS,
    "GPS_fixType": {
        0: "No GPS", 1: "No Fix", 2: "2D Fix", 3: "3D Fix",
        4: "DGPS", 5: "RTK Float", 6: "RTK Fixed",
    },
}

INAV_PARAMS = [
    # Core Attitude & Position
    {"name": "Altitude (Rel)", "param": "pos_z", "desc": "Relative altitude from the takeoff point based on Baro/GPS fusion.", "unit": "m", "color": "#00ff00", "plot": True, "trail": True},
    {"name": "Roll Angle", "param": "attitude[0]", "desc": "Aircraft lean angle on the roll axis (left/right).", "unit": "deg", "color": "#ff00ff", "plot": True, "trail": True},
    {"name": "Pitch Angle", "param": "attitude[1]", "desc": "Aircraft tilt angle on the pitch axis (nose up/down).", "unit": "deg", "color": "#00ffff", "plot": True, "trail": True},
    {"name": "Yaw (Heading)", "param": "attitude[2]", "desc": "Stabilized heading relative to magnetic North.", "unit": "deg", "color": "#ffff00", "plot": True, "trail": False},
    
    # Power System
    {"name": "Battery Voltage", "param": "vbat (V)", "desc": "Main flight battery voltage (uncompensated).", "unit": "V", "color": "#ffff00", "plot": True, "trail": True},
    {"name": "Current Draw", "param": "amperage (A)", "desc": "Real-time total current draw from the battery.", "unit": "A", "color": "#ff3333", "plot": True, "trail": True},
    {"name": "Battery Used", "param": "energyCumulative (mAh)", "desc": "Total battery capacity consumed since power-on.", "unit": "mAh", "color": "#ff6666", "plot": False, "trail": False},
    {"name": "Sag Comp VBat", "param": "sagCompensatedVBat", "desc": "Estimated battery voltage compensated for load sag.", "unit": "V", "color": "#ffcc00", "plot": False, "trail": False},
    
    # GPS & Navigation
    {"name": "GPS Satellites", "param": "GPS_numSat", "desc": "Number of satellites used for the current 3D fix.", "unit": "", "color": "#ffffff", "plot": True, "trail": True},
    {"name": "GPS Ground Speed", "param": "GPS_speed (m/s)", "desc": "Horizontal speed over ground measured by GPS.", "unit": "m/s", "color": "#00ffff", "plot": False, "trail": True},
    {"name": "GPS Course", "param": "GPS_ground_course", "desc": "Actual direction of travel over ground (COG).", "unit": "deg", "color": "#ffff00", "plot": False, "trail": False},
    {"name": "GPS Altitude (MSL)", "param": "GPS_altitude", "desc": "Absolute altitude above Mean Sea Level.", "unit": "m", "color": "#00ff00", "plot": False, "trail": False},
    {"name": "GPS Fix Type", "param": "GPS_fixType", "desc": "Type of GPS lock (2D, 3D, etc.).", "unit": "", "color": "#ffffff", "plot": False, "trail": False, "can_plot": False},
    {"name": "GPS Precision (HDOP)", "param": "GPS_hdop", "desc": "Horizontal Dilution of Precision (lower is better).", "unit": "", "color": "#ffaa00", "plot": False, "trail": False},
    {"name": "Nav Error (H)", "param": "navEPH", "desc": "Estimated Horizontal Position Error (cm).", "unit": "cm", "color": "#ff5555", "plot": False, "trail": False},
    {"name": "Nav Error (V)", "param": "navEPV", "desc": "Estimated Vertical Position Error (cm).", "unit": "cm", "color": "#ff5555", "plot": False, "trail": False},
    
    # Controller Outputs
    {"name": "Motor 1 Output", "param": "motor[0]", "desc": "PWM signal sent to the first motor (throttle).", "unit": "", "color": "#ffaa00", "plot": True, "trail": True},
    {"name": "Motor 2 Output", "param": "motor[1]", "desc": "PWM signal sent to the second motor.", "unit": "", "color": "#ff5500", "plot": True, "trail": True},
    {"name": "servo[0]", "param": "servo[0]", "desc": "PWM output position for the first servo.", "unit": "", "color": "#888888", "plot": True, "trail": False},
    {"name": "servo[1]", "param": "servo[1]", "desc": "PWM output position for the second servo.", "unit": "", "color": "#444444", "plot": True, "trail": False},
    {"name": "servo[2]", "param": "servo[2]", "desc": "PWM output position for servo channel 3.", "unit": "", "color": "#888888", "plot": False, "trail": False},
    
    # Radio & Telemetry
    {"name": "RSSI", "param": "rssi", "desc": "Received Signal Strength Indicator.", "unit": "", "color": "#ffffff", "plot": True, "trail": True},
    {"name": "Link Quality", "param": "rxUpdateRate", "desc": "Number of valid RC frames received per second.", "unit": "Hz", "color": "#00ff00", "plot": False, "trail": False},
    
    # IMU & Environment
    {"name": "IMU Temp", "param": "IMUTemperature", "desc": "Internal temperature of the IMU sensor.", "unit": "°C", "color": "#ffaa00", "plot": False, "trail": True},
    {"name": "Baro Temp", "param": "baroTemperature", "desc": "Temperature measured by the barometer sensor.", "unit": "°C", "color": "#ffcc00", "plot": False, "trail": True},
    
    # RC Inputs (Pilot Input)
    {"name": "RC Roll Stick", "param": "rcData[0]", "desc": "Raw roll stick position from the receiver (typically 1000-2000us).", "unit": "us", "color": "#ff00ff", "plot": True},
    {"name": "RC Pitch Stick", "param": "rcData[1]", "desc": "Raw pitch stick position from the receiver.", "unit": "us", "color": "#00ffff", "plot": False},
    {"name": "RC Yaw Stick", "param": "rcData[2]", "desc": "Raw yaw stick position from the receiver.", "unit": "us", "color": "#ffff00", "plot": False},
    {"name": "RC Throttle Stick", "param": "rcData[3]", "desc": "Raw throttle stick position from the receiver.", "unit": "us", "color": "#ffffff", "plot": False},
    
    {"name": "RC Roll Cmd", "param": "rcCommand[0]", "desc": "Processed roll command sent to the PID controller.", "unit": "", "color": "#ff00ff", "plot": False},
    {"name": "RC Pitch Cmd", "param": "rcCommand[1]", "desc": "Processed pitch command sent to the PID controller.", "unit": "", "color": "#00ffff", "plot": False},
    {"name": "RC Yaw Cmd", "param": "rcCommand[2]", "desc": "Processed yaw command sent to the PID controller.", "unit": "", "color": "#ffff00", "plot": False},
    {"name": "RC Throttle Cmd", "param": "rcCommand[3]", "desc": "Requested throttle percentage from the transmitter.", "unit": "", "color": "#ffffff", "plot": True, "trail": True},

    # Navigation & Targets
    {"name": "Navigation State", "param": "navState", "desc": "Current state of the navigation controller.", "unit": "", "color": "#00ffff", "plot": False, "can_plot": False, "trail": True},
    {"name": "Nav Pos North", "param": "navPos[0]", "desc": "Current North position relative to takeoff point (cm).", "unit": "cm", "color": "#ffffff", "plot": False},
    {"name": "Nav Pos East", "param": "navPos[1]", "desc": "Current East position relative to takeoff point (cm).", "unit": "cm", "color": "#ffffff", "plot": False},
    {"name": "Nav Target Hdg", "param": "navTgtHdg", "desc": "Target heading requested by the navigation controller.", "unit": "deg", "color": "#00ff00", "plot": False},
    {"name": "Active Waypoint", "param": "activeWpNumber", "desc": "The index of the currently targeted navigation waypoint.", "unit": "", "color": "#00ff00", "plot": False},

    # Air & Environment
    {"name": "Airspeed", "param": "AirSpeed", "desc": "True speed relative to the surrounding air.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "Wind North", "param": "wind[0]", "desc": "Estimated wind component from the North.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "Wind East", "param": "wind[1]", "desc": "Estimated wind component from the East.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "ESC RPM", "param": "escRPM", "desc": "Motor rotations per minute reported by the ESC.", "unit": "RPM", "color": "#00ff00", "plot": False, "trail": True},
    {"name": "ESC Temp", "param": "escTemperature", "desc": "Internal temperature of the ESC MOSFETs.", "unit": "°C", "color": "#ff5555", "plot": False, "trail": True},

    # System Status
    {"name": "Flight Modes", "param": "flightModeFlags (flags)", "desc": "Bitmask of active flight modes (Angle, Horizon, RTH, etc.).", "unit": "", "color": "#ffffff", "plot": False, "can_plot": False},
    {"name": "Failsafe Phase", "param": "failsafePhase (flags)", "desc": "Current phase of the failsafe system.", "unit": "", "color": "#ff0000", "plot": False, "can_plot": False},
]

ARDUPILOT_PARAMS = [
    # Core Attitude & Position
    {"name": "Altitude (Rel)", "param": "pos_z", "desc": "Fused relative altitude above the home point (takeoff location). Derived from EKF fusion of Baro, GPS, and IMU.", "unit": "m", "color": "#00ff00", "plot": True, "trail": True},
    {"name": "Roll Angle", "param": "attitude[0]", "desc": "Actual measured aircraft roll attitude relative to the horizon.", "unit": "deg", "color": "#ff00ff", "plot": True, "trail": True},
    {"name": "Pitch Angle", "param": "attitude[1]", "desc": "Actual measured aircraft pitch attitude (nose up/down).", "unit": "deg", "color": "#00ffff", "plot": True, "trail": True},
    {"name": "Yaw (Heading)", "param": "attitude[2]", "desc": "Actual stabilized magnetic heading of the aircraft (0-360 degrees).", "unit": "deg", "color": "#ffff00", "plot": True, "trail": False},
    
    # Commanded (Setpoints)
    {"name": "Desired Roll", "param": "Desired Roll", "desc": "Target roll angle requested by the flight controller or pilot input in stabilized modes.", "unit": "deg", "color": "#ff66ff", "plot": False},
    {"name": "Desired Pitch", "param": "Desired Pitch", "desc": "Target pitch angle requested by the flight controller (nose position setpoint).", "unit": "deg", "color": "#66ffff", "plot": False},
    {"name": "Desired Yaw", "param": "Desired Yaw", "desc": "Target heading requested by the flight controller (navigation or pilot setpoint).", "unit": "deg", "color": "#ffff66", "plot": False},
    {"name": "Desired Altitude (Copter)", "param": "Desired Altitude (Copter)", "desc": "Target altitude setpoint for Copter/Quad modes (CTUN.DAlt).", "unit": "m", "color": "#00ffaa", "plot": False},
    {"name": "Desired Altitude (Quad)", "param": "Desired Altitude (Quad)", "desc": "Target altitude setpoint for QuadPlane vertical flight modes (QTUN.DAlt).", "unit": "m", "color": "#00ffaa", "plot": False},
    
    # Power System
    {"name": "Battery Voltage", "param": "vbat (V)", "desc": "Main flight battery voltage as measured by the power module (BAT.Volt).", "unit": "V", "color": "#ffff00", "plot": True, "trail": True},
    {"name": "Current Draw", "param": "amperage (A)", "desc": "Real-time battery current draw in Amperes (BAT.Curr).", "unit": "A", "color": "#ff3333", "plot": True, "trail": True},
    {"name": "Battery Used", "param": "energyCumulative (mAh)", "desc": "Total battery capacity consumed since power-on (BAT.CurrTot).", "unit": "mAh", "color": "#ff6666", "plot": False},
    {"name": "Battery Remaining", "param": "batteryRemaining", "desc": "Estimated percentage of battery capacity remaining based on capacity settings.", "unit": "%", "color": "#ffcc00", "plot": False},
    
    # GPS & Navigation
    {"name": "GPS Latitude", "param": "GPS_coord[0]", "desc": "Raw GPS latitude coordinate. Used for ground track and RTH navigation.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "GPS Longitude", "param": "GPS_coord[1]", "desc": "Raw GPS longitude coordinate. Used for ground track and RTH navigation.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "GPS Satellites", "param": "GPS_numSat", "desc": "Number of satellites currently used in the 3D fix (GPS.NSats).", "unit": "", "color": "#ffffff", "plot": True},
    {"name": "GPS Ground Speed", "param": "GPS_speed (m/s)", "desc": "Horizontal speed over ground reported by the GPS receiver (GPS.Spd).", "unit": "m/s", "color": "#00ffff", "plot": False},
    {"name": "GPS Course", "param": "GPS_ground_course", "desc": "Direction of travel (Course Over Ground) reported by the GPS (GPS.GCrs).", "unit": "deg", "color": "#ffff00", "plot": False},
    {"name": "GPS Altitude (MSL)", "param": "GPS_altitude", "desc": "Absolute altitude above Mean Sea Level reported by the GPS receiver (GPS.Alt).", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "GPS HDOP", "param": "GPS_hdop", "desc": "Horizontal Dilution of Precision. Accuracy indicator where lower is better (GPS.HDop).", "unit": "", "color": "#ffaa00", "plot": False},
    {"name": "GPS Fix Type", "param": "GPS_fixType", "desc": "Type of GPS lock reported by ArduPilot GPS.Status.", "unit": "", "color": "#ffffff", "plot": False, "can_plot": False},
    {"name": "GPS Vertical Velocity", "param": "GPS_VZ", "desc": "Vertical speed measured directly by the GPS (GPS.VZ).", "unit": "m/s", "color": "#ff55ff", "plot": False},

    # EKF Position Estimates (Fuzed Data)
    {"name": "EKF Latitude", "param": "POS_Lat", "desc": "Fused latitude estimate from the Extended Kalman Filter (EKF). Highest precision position.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "EKF Longitude", "param": "POS_Lng", "desc": "Fused longitude estimate from the Extended Kalman Filter (EKF). Highest precision position.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "EKF Altitude (MSL)", "param": "POS_Alt", "desc": "Fused absolute altitude above Mean Sea Level from the EKF (POS.Alt).", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "EKF Rel Home Alt", "param": "POS_RelHomeAlt", "desc": "Fused altitude relative to the Home (takeoff) location (POS.RelHomeAlt).", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "EKF Rel Origin Alt", "param": "POS_RelOriginAlt", "desc": "Fused altitude relative to the EKF origin point (POS.RelOriginAlt).", "unit": "m", "color": "#00ff00", "plot": False},

    # Controller Outputs
    {"name": "Throttle (Commanded)", "param": "Throttle (Commanded)", "desc": "Normalized throttle command (0.0 to 1.0) output by the flight controller logic.", "unit": "", "color": "#ffffff", "plot": True},
    {"name": "TECS Altitude", "param": "TECS Altitude", "desc": "Altitude used by the Total Energy Control System (TECS.h).", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "TECS Desired Alt", "param": "TECS Desired Alt", "desc": "Target altitude requested by the TECS controller (TECS.h_dem).", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "TECS Airspeed", "param": "TECS Airspeed", "desc": "Current airspeed used by the TECS controller for energy calculation (TECS.v).", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "TECS Desired Airspeed", "param": "TECS Desired Airspeed", "desc": "Target airspeed requested by the TECS controller (TECS.v_dem).", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "TECS Desired Pitch", "param": "TECS Desired Pitch", "desc": "Pitch angle requested by the TECS controller to manage energy (TECS.ptch).", "unit": "deg", "color": "#00ffff", "plot": False},
    {"name": "Throttle Out (Copter)", "param": "Throttle Out (Copter)", "desc": "Final throttle output percentage for Copter/Multi-rotor (CTUN.ThO).", "unit": "%", "color": "#ffffff", "plot": False},
    {"name": "Throttle Out (Quad)", "param": "Throttle Out (Quad)", "desc": "Final throttle output percentage for QuadPlane motors (QTUN.ThO).", "unit": "%", "color": "#ffffff", "plot": False},

    {"name": "Output 1 (M1)", "param": "motor[0]", "desc": "PWM output for first identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": True},
    {"name": "Output 2 (M2)", "param": "motor[1]", "desc": "PWM output for second identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    {"name": "Output 3 (M3)", "param": "motor[2]", "desc": "PWM output for third identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "Output 4 (M4)", "param": "motor[3]", "desc": "PWM output for fourth identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    {"name": "Output 5 (M5)", "param": "motor[4]", "desc": "PWM output for fifth identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "Output 6 (M6)", "param": "motor[5]", "desc": "PWM output for sixth identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    {"name": "Output 7 (M7)", "param": "motor[6]", "desc": "PWM output for seventh identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "Output 8 (M8)", "param": "motor[7]", "desc": "PWM output for eighth identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    {"name": "Output 9 (M9)", "param": "motor[8]", "desc": "PWM output for ninth identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "Output 10 (M10)", "param": "motor[9]", "desc": "PWM output for tenth identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    {"name": "Output 11 (M11)", "param": "motor[10]", "desc": "PWM output for eleventh identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "Output 12 (M12)", "param": "motor[11]", "desc": "PWM output for twelfth identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    {"name": "Output 13 (M13)", "param": "motor[12]", "desc": "PWM output for thirteenth identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "Output 14 (M14)", "param": "motor[13]", "desc": "PWM output for fourteenth identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    {"name": "Output 15 (M15)", "param": "motor[14]", "desc": "PWM output for fifteenth identified motor channel.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "Output 16 (M16)", "param": "motor[15]", "desc": "PWM output for sixteenth identified motor channel.", "unit": "us", "color": "#ff5500", "plot": False},
    
    {"name": "Servo 1 Out", "param": "servo[0]", "desc": "PWM output for first identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 2 Out", "param": "servo[1]", "desc": "PWM output for second identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    {"name": "Servo 3 Out", "param": "servo[2]", "desc": "PWM output for third identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 4 Out", "param": "servo[3]", "desc": "PWM output for fourth identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    {"name": "Servo 5 Out", "param": "servo[4]", "desc": "PWM output for fifth identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 6 Out", "param": "servo[5]", "desc": "PWM output for sixth identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    {"name": "Servo 7 Out", "param": "servo[6]", "desc": "PWM output for seventh identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 8 Out", "param": "servo[7]", "desc": "PWM output for eighth identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    {"name": "Servo 9 Out", "param": "servo[8]", "desc": "PWM output for ninth identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 10 Out", "param": "servo[9]", "desc": "PWM output for tenth identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    {"name": "Servo 11 Out", "param": "servo[10]", "desc": "PWM output for eleventh identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 12 Out", "param": "servo[11]", "desc": "PWM output for twelfth identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    {"name": "Servo 13 Out", "param": "servo[12]", "desc": "PWM output for thirteenth identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 14 Out", "param": "servo[13]", "desc": "PWM output for fourteenth identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    {"name": "Servo 15 Out", "param": "servo[14]", "desc": "PWM output for fifteenth identified control surface channel.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "Servo 16 Out", "param": "servo[15]", "desc": "PWM output for sixteenth identified control surface channel.", "unit": "us", "color": "#444444", "plot": False},
    
    # RC Stick Inputs (Pilot)
    {"name": "RC Roll Stick", "param": "rcData[0]", "desc": "Pilot raw roll input (CH1, typically 1000-2000us).", "unit": "us", "color": "#ff00ff", "plot": True},
    {"name": "RC Pitch Stick", "param": "rcData[1]", "desc": "Pilot raw pitch input (CH2).", "unit": "us", "color": "#00ffff", "plot": False},
    {"name": "RC Throttle Stick", "param": "rcData[3]", "desc": "Pilot raw throttle input (CH3).", "unit": "us", "color": "#ffffff", "plot": False},
    {"name": "RC Yaw Stick", "param": "rcData[2]", "desc": "Pilot raw yaw input (CH4).", "unit": "us", "color": "#ffff00", "plot": False},
    {"name": "RC Aux 1 (CH5)", "param": "rcData[4]", "desc": "Pilot auxiliary channel 5 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 2 (CH6)", "param": "rcData[5]", "desc": "Pilot auxiliary channel 6 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 3 (CH7)", "param": "rcData[6]", "desc": "Pilot auxiliary channel 7 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 4 (CH8)", "param": "rcData[7]", "desc": "Pilot auxiliary channel 8 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 5 (CH9)", "param": "rcData[8]", "desc": "Pilot auxiliary channel 9 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 6 (CH10)", "param": "rcData[9]", "desc": "Pilot auxiliary channel 10 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 7 (CH11)", "param": "rcData[10]", "desc": "Pilot auxiliary channel 11 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 8 (CH12)", "param": "rcData[11]", "desc": "Pilot auxiliary channel 12 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 9 (CH13)", "param": "rcData[12]", "desc": "Pilot auxiliary channel 13 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 10 (CH14)", "param": "rcData[13]", "desc": "Pilot auxiliary channel 14 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 11 (CH15)", "param": "rcData[14]", "desc": "Pilot auxiliary channel 15 input.", "unit": "us", "color": "#888888", "plot": False},
    {"name": "RC Aux 12 (CH16)", "param": "rcData[15]", "desc": "Pilot auxiliary channel 16 input.", "unit": "us", "color": "#888888", "plot": False},

    # Sensors & Environment
    {"name": "IMU Temp", "param": "IMUTemperature", "desc": "Internal temperature of the primary IMU sensor (IMU.T).", "unit": "°C", "color": "#ffaa00", "plot": False},
    {"name": "Battery Temp", "param": "Temp", "desc": "Temperature reported by the battery monitor/power module (BAT.Temp).", "unit": "°C", "color": "#ffaa00", "plot": False},
    {"name": "Baro Altitude", "param": "BaroAlt (cm)", "desc": "Filtered barometric altitude calculated from pressure sensor data (BARO.Alt).", "unit": "cm", "color": "#00ff00", "plot": False},
    
    {"name": "Gyro X", "param": "gyroADC[0]", "desc": "Raw angular velocity around the X axis (Roll) from IMU.GyrX.", "unit": "rad/s", "color": "#ff00ff", "plot": False},
    {"name": "Gyro Y", "param": "gyroADC[1]", "desc": "Raw angular velocity around the Y axis (Pitch) from IMU.GyrY.", "unit": "rad/s", "color": "#00ffff", "plot": False},
    {"name": "Gyro Z", "param": "gyroADC[2]", "desc": "Raw angular velocity around the Z axis (Yaw) from IMU.GyrZ.", "unit": "rad/s", "color": "#ffff00", "plot": False},
    
    {"name": "Accel X", "param": "accSmooth[0]", "desc": "Acceleration on the X axis scaled to the INAV 2048 LSB/G convention for shared stats code.", "unit": "LSB", "color": "#ff00ff", "plot": False},
    {"name": "Accel Y", "param": "accSmooth[1]", "desc": "Acceleration on the Y axis scaled to the INAV 2048 LSB/G convention for shared stats code.", "unit": "LSB", "color": "#00ffff", "plot": False},
    {"name": "Accel Z", "param": "accSmooth[2]", "desc": "Acceleration on the Z axis scaled to the INAV 2048 LSB/G convention for shared stats code.", "unit": "LSB", "color": "#ffff00", "plot": False},
    
    {"name": "Mag X", "param": "magADC[0]", "desc": "Raw magnetic field strength on the X axis (milli-Gauss).", "unit": "mG", "color": "#ff00ff", "plot": False},
    {"name": "Mag Y", "param": "magADC[1]", "desc": "Raw magnetic field strength on the Y axis (milli-Gauss).", "unit": "mG", "color": "#00ffff", "plot": False},
    {"name": "Mag Z", "param": "magADC[2]", "desc": "Raw magnetic field strength on the Z axis (milli-Gauss).", "unit": "mG", "color": "#ffff00", "plot": False},

    {"name": "Vibration X", "param": "vibeX", "desc": "Vibration level on the X axis. High values indicate mechanical imbalance (VIBE.VibeX).", "unit": "", "color": "#888888", "plot": False},
    {"name": "Vibration Y", "param": "vibeY", "desc": "Vibration level on the Y axis. High values indicate mechanical imbalance (VIBE.VibeY).", "unit": "", "color": "#888888", "plot": False},
    {"name": "Vibration Z", "param": "vibeZ", "desc": "Vibration level on the Z axis. High values indicate mechanical imbalance (VIBE.VibeZ).", "unit": "", "color": "#888888", "plot": False},

    # System Status
    {"name": "Is Flying", "param": "isFlying", "desc": "Safety logic flag indicating if the vehicle is currently airborne (1) or landed (0).", "unit": "bool", "color": "#00ffff", "plot": False},
    {"name": "Armed", "param": "Armed", "desc": "Safety status flag. 1 means motors are armed and active; 0 means disarmed.", "unit": "bool", "color": "#00ff00", "plot": False},
    {"name": "Flight Mode", "param": "Mode", "desc": "Name of the active ArduPilot flight mode (e.g., FBWA, LOITER, AUTO).", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Flight Mode Num", "param": "ModeNum", "desc": "Numerical ID of the active flight mode used by the internal firmware logic.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Status Flags", "param": "stateFlags (flags)", "desc": "Combined system status flags for flight readiness and safety.", "unit": "", "color": "#00ff00", "plot": False, "can_plot": False},
    {"name": "Flight Mode Flags", "param": "flightModeFlags (flags)", "desc": "Flight mode selction status flags", "unit": "", "color": "#ffffff", "plot": False, "can_plot": False, "trail": True},
    {"name": "Event ID", "param": "EventId", "desc": "Logged ID for software or hardware events (mode changes, failsafes, errors).", "unit": "", "color": "#ff0000", "plot": False},
]

ARDUPILOT_EXTRA_PARAMS = [
    # Attitude/GPS detail from the Mission Planner log-analysis page
    {"name": "Attitude Error RP", "param": "Attitude Err Roll/Pitch", "desc": "Average roll/pitch attitude estimate error from ATT.ErrRP.", "unit": "", "color": "#ff99ff", "plot": False},
    {"name": "Attitude Error Yaw", "param": "Attitude Err Yaw", "desc": "Yaw attitude estimate error from ATT.ErrYaw.", "unit": "", "color": "#ffff99", "plot": False},
    {"name": "GPS Relative Alt", "param": "GPS_rel_altitude", "desc": "Accelerometer and barometer altitude relative to home from GPS.RelAlt, when present.", "unit": "m", "color": "#00cc66", "plot": False},
    {"name": "GPS Time", "param": "GPS_time_ms", "desc": "GPS time-of-week in milliseconds from GPS.GMS.", "unit": "ms", "color": "#cccccc", "plot": False},
    {"name": "GPS Week", "param": "GPS_week", "desc": "GPS week number from GPS.GWk.", "unit": "", "color": "#cccccc", "plot": False},

    # Compass detail
    {"name": "Mag Offset X", "param": "Mag Offset X", "desc": "Compass X-axis offset from MAG.OfsX.", "unit": "", "color": "#ff00ff", "plot": False},
    {"name": "Mag Offset Y", "param": "Mag Offset Y", "desc": "Compass Y-axis offset from MAG.OfsY.", "unit": "", "color": "#00ffff", "plot": False},
    {"name": "Mag Offset Z", "param": "Mag Offset Z", "desc": "Compass Z-axis offset from MAG.OfsZ.", "unit": "", "color": "#ffff00", "plot": False},
    {"name": "Mag Motor Offset X", "param": "Mag Motor Offset X", "desc": "Compass/motor compensation X value from MAG.MOX.", "unit": "", "color": "#cc66ff", "plot": False},
    {"name": "Mag Motor Offset Y", "param": "Mag Motor Offset Y", "desc": "Compass/motor compensation Y value from MAG.MOY.", "unit": "", "color": "#66ffff", "plot": False},
    {"name": "Mag Motor Offset Z", "param": "Mag Motor Offset Z", "desc": "Compass/motor compensation Z value from MAG.MOZ.", "unit": "", "color": "#ffff66", "plot": False},
    {"name": "Mag Health", "param": "Mag Health", "desc": "Compass health flag from MAG.Health.", "unit": "", "color": "#ffffff", "plot": False},

    # Copter control tuning fields
    {"name": "Throttle In (Copter)", "param": "Throttle In (Copter)", "desc": "Pilot throttle input from CTUN.ThI.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Throttle Hover (Copter)", "param": "Throttle Hover (Copter)", "desc": "Estimated hover throttle from CTUN.ThH.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "Throttle Desired (Copter)", "param": "Throttle Desired (Copter)", "desc": "Desired throttle from CTUN.ThD.", "unit": "", "color": "#dddddd", "plot": False},
    {"name": "Control Altitude (Copter)", "param": "Control Altitude (Copter)", "desc": "Controller altitude from CTUN.Alt.", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "Baro Altitude (Copter)", "param": "Baro Altitude (Copter)", "desc": "Barometer altitude from CTUN.BAlt.", "unit": "m", "color": "#00cc66", "plot": False},
    {"name": "Sonar Altitude (Copter)", "param": "Sonar Altitude (Copter)", "desc": "Rangefinder/sonar altitude from CTUN.SAlt.", "unit": "m", "color": "#66ff66", "plot": False},
    {"name": "Terrain Altitude (Copter)", "param": "Terrain Altitude (Copter)", "desc": "Terrain altitude from CTUN.TAlt.", "unit": "m", "color": "#99ff99", "plot": False},
    {"name": "Desired Climb Rate", "param": "Desired Climb Rate (Copter)", "desc": "Desired climb rate from CTUN.DCRt.", "unit": "cm/s", "color": "#00ffaa", "plot": False},
    {"name": "Climb Rate", "param": "Climb Rate (Copter)", "desc": "Actual climb rate from CTUN.CRt.", "unit": "cm/s", "color": "#00ccaa", "plot": False},
    {"name": "Harmonic Notch Freq", "param": "Harmonic Notch Freq", "desc": "Current harmonic notch center frequency from CTUN.N.", "unit": "Hz", "color": "#ffaa00", "plot": False},

    # Navigation tuning
    {"name": "WP Distance", "param": "WP Distance", "desc": "Distance to next waypoint or loiter target from NTUN.WPDst/Dist.", "unit": "cm", "color": "#ffffff", "plot": False},
    {"name": "WP Bearing", "param": "WP Bearing", "desc": "Bearing to next waypoint from NTUN.WPBrg/TBrg.", "unit": "deg", "color": "#ffff00", "plot": False},
    {"name": "Nav Bearing", "param": "Nav Bearing", "desc": "Current navigation bearing from NTUN.NavBrg.", "unit": "deg", "color": "#ffff66", "plot": False},
    {"name": "Altitude Error", "param": "Altitude Error", "desc": "Altitude error from NTUN.AltE.", "unit": "m", "color": "#ff5555", "plot": False},
    {"name": "Cross Track Error", "param": "Cross Track Error", "desc": "Cross-track navigation error from NTUN.XT.", "unit": "m", "color": "#ff7777", "plot": False},
    {"name": "Cross Track Integral", "param": "Cross Track Integral", "desc": "Integrated cross-track navigation error from NTUN.XTi.", "unit": "", "color": "#ff9999", "plot": False},
    {"name": "Target Airspeed", "param": "Target Airspeed", "desc": "Navigation target airspeed from NTUN.TAsp.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "Position Error X", "param": "Position Error X", "desc": "Navigation position error in the latitude/North direction from NTUN.PErX.", "unit": "cm", "color": "#ff5555", "plot": False},
    {"name": "Position Error Y", "param": "Position Error Y", "desc": "Navigation position error in the longitude/East direction from NTUN.PErY.", "unit": "cm", "color": "#ff7777", "plot": False},
    {"name": "Desired Velocity X", "param": "Desired Velocity X", "desc": "Desired velocity in the latitude/North direction from NTUN.DVelX.", "unit": "cm/s", "color": "#55ccff", "plot": False},
    {"name": "Desired Velocity Y", "param": "Desired Velocity Y", "desc": "Desired velocity in the longitude/East direction from NTUN.DVelY.", "unit": "cm/s", "color": "#77ddff", "plot": False},
    {"name": "Velocity X", "param": "Velocity X", "desc": "Actual velocity estimate in the latitude/North direction from NTUN.VelX.", "unit": "cm/s", "color": "#55ffaa", "plot": False},
    {"name": "Velocity Y", "param": "Velocity Y", "desc": "Actual velocity estimate in the longitude/East direction from NTUN.VelY.", "unit": "cm/s", "color": "#77ffbb", "plot": False},
    {"name": "Desired Accel X", "param": "Desired Accel X", "desc": "Desired acceleration in the latitude/North direction from NTUN.DAcX.", "unit": "cm/s/s", "color": "#5599ff", "plot": False},
    {"name": "Desired Accel Y", "param": "Desired Accel Y", "desc": "Desired acceleration in the longitude/East direction from NTUN.DAcY.", "unit": "cm/s/s", "color": "#77aaff", "plot": False},
    {"name": "Nav Desired Roll", "param": "Desired Roll Nav", "desc": "Navigation desired roll angle from NTUN.DRol.", "unit": "cdeg", "color": "#ff99ff", "plot": False},
    {"name": "Nav Desired Pitch", "param": "Desired Pitch Nav", "desc": "Navigation desired pitch angle from NTUN.DPit.", "unit": "cdeg", "color": "#99ffff", "plot": False},

    # GPS accuracy and system performance
    {"name": "GPS VDOP", "param": "GPS VDOP", "desc": "Vertical dilution of precision from GPA.VDop.", "unit": "", "color": "#ffaa00", "plot": False},
    {"name": "GPS HAcc", "param": "GPS Horizontal Accuracy", "desc": "GPS horizontal accuracy from GPA.HAcc.", "unit": "m", "color": "#ffaa00", "plot": False},
    {"name": "GPS VAcc", "param": "GPS Vertical Accuracy", "desc": "GPS vertical accuracy from GPA.VAcc.", "unit": "m", "color": "#ffaa00", "plot": False},
    {"name": "GPS SAcc", "param": "GPS Speed Accuracy", "desc": "GPS speed accuracy from GPA.SAcc.", "unit": "m/s", "color": "#ffaa00", "plot": False},
    {"name": "GPS VV Valid", "param": "GPS Vertical Velocity Valid", "desc": "Flag indicating whether GPS vertical velocity is valid from GPA.VV.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "GPS Sample Time", "param": "GPS Sample Time", "desc": "Autopilot timestamp associated with GPS accuracy data from GPA.SMS.", "unit": "ms", "color": "#cccccc", "plot": False},
    {"name": "GPS Delta Time", "param": "GPS Delta Time", "desc": "Elapsed time between parsed GPS samples from GPA.Delta.", "unit": "ms", "color": "#cccccc", "plot": False},
    {"name": "PM Long Loops", "param": "PM Long Loops", "desc": "Number of long-running scheduler loops from PM.NLon.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "PM Loop Count", "param": "PM Loop Count", "desc": "Loop count for the PM sample from PM.NLoop.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "PM Max Loop Time", "param": "PM Max Loop Time", "desc": "Maximum scheduler loop time from PM.MaxT.", "unit": "us", "color": "#ffaa00", "plot": False},
    {"name": "PM Free Memory", "param": "PM Free Memory", "desc": "Available memory from PM.Mem.", "unit": "bytes", "color": "#ffffff", "plot": False},
    {"name": "PM CPU Load", "param": "PM CPU Load", "desc": "Scheduler CPU load from PM.Load.", "unit": "", "color": "#ffaa00", "plot": False},

    # Sparse event/detail messages
    {"name": "Error Subsystem", "param": "Error Subsystem", "desc": "ERR.Subsys value for logged ArduPilot errors.", "unit": "", "color": "#ff0000", "plot": False},
    {"name": "Error Code", "param": "Error Code", "desc": "ERR.ECode value for logged ArduPilot errors.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "AutoTune Axis", "param": "AutoTune Axis", "desc": "AutoTune axis from ATUN.Axis.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "AutoTune Step", "param": "AutoTune Step", "desc": "AutoTune step from ATUN.TuneStep.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "AutoTune Rate Min", "param": "AutoTune Rate Min", "desc": "Minimum recorded AutoTune rate from ATUN.RateMin.", "unit": "", "color": "#55ccff", "plot": False},
    {"name": "AutoTune Rate Max", "param": "AutoTune Rate Max", "desc": "Maximum recorded AutoTune rate from ATUN.RateMax.", "unit": "", "color": "#77ddff", "plot": False},
    {"name": "AutoTune RP Gain", "param": "AutoTune RP Gain", "desc": "Rate P gain being tested from ATUN.RPGain.", "unit": "", "color": "#ff99ff", "plot": False},
    {"name": "AutoTune RD Gain", "param": "AutoTune RD Gain", "desc": "Rate D gain being tested from ATUN.RDGain.", "unit": "", "color": "#ff77ff", "plot": False},
    {"name": "AutoTune SP Gain", "param": "AutoTune SP Gain", "desc": "Stabilize P gain being tested from ATUN.SPGain.", "unit": "", "color": "#ff55ff", "plot": False},
    {"name": "AutoTune Angle", "param": "AutoTune Angle", "desc": "AutoTune test angle from ATDE.Angle.", "unit": "cdeg", "color": "#00ffff", "plot": False},
    {"name": "AutoTune Rate", "param": "AutoTune Rate", "desc": "AutoTune rotation rate from ATDE.Rate.", "unit": "", "color": "#00cccc", "plot": False},
]

ARDUPILOT_CAM_CMD_PARAMS = [
    {"name": "Camera GPS Time", "param": "CAM_GPSTime", "desc": "GPS time when camera shutter was activated from CAM.GPSTime.", "unit": "ms", "color": "#cccccc", "plot": False},
    {"name": "Camera Lat", "param": "CAM_Lat", "desc": "Camera event latitude from CAM.Lat.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "Camera Lng", "param": "CAM_Lng", "desc": "Camera event longitude from CAM.Lng.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "Camera Alt", "param": "CAM_Alt", "desc": "Camera event altitude from CAM.Alt.", "unit": "cm", "color": "#00ff00", "plot": False},
    {"name": "Camera Roll", "param": "CAM_Roll", "desc": "Vehicle roll at camera event from CAM.Roll.", "unit": "cdeg", "color": "#ff00ff", "plot": False},
    {"name": "Camera Pitch", "param": "CAM_Pitch", "desc": "Vehicle pitch at camera event from CAM.Pitch.", "unit": "cdeg", "color": "#00ffff", "plot": False},
    {"name": "Camera Yaw", "param": "CAM_Yaw", "desc": "Vehicle yaw at camera event from CAM.Yaw.", "unit": "cdeg", "color": "#ffff00", "plot": False},
    {"name": "Command Total", "param": "CMD_CTot", "desc": "Total mission command count from CMD.CTot.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Command Number", "param": "CMD_CNum", "desc": "Mission command number from CMD.CNum.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Command ID", "param": "CMD_CId", "desc": "MAVLink command ID from CMD.CId.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Command Option", "param": "CMD_Copt", "desc": "Command option value from CMD.Copt, when present.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "Command Param 1", "param": "CMD_Prm1", "desc": "Mission command parameter 1 from CMD.Prm1.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "Command Param 2", "param": "CMD_Prm2", "desc": "Mission command parameter 2 from CMD.Prm2.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "Command Param 3", "param": "CMD_Prm3", "desc": "Mission command parameter 3 from CMD.Prm3.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "Command Param 4", "param": "CMD_Prm4", "desc": "Mission command parameter 4 from CMD.Prm4.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "Command Alt", "param": "CMD_Alt", "desc": "Mission command altitude from CMD.Alt.", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "Command Lat", "param": "CMD_Lat", "desc": "Mission command latitude from CMD.Lat.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "Command Lng", "param": "CMD_Lng", "desc": "Mission command longitude from CMD.Lng.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "D32 ID", "param": "D32_Id", "desc": "Signed 32-bit diagnostic value ID from D32.Id.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "D32 Value", "param": "D32_Value", "desc": "Signed 32-bit diagnostic value from D32.Value.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "DU32 ID", "param": "DU32_Id", "desc": "Unsigned 32-bit diagnostic value ID from DU32.Id.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "DU32 Value", "param": "DU32_Value", "desc": "Unsigned 32-bit diagnostic value from DU32.Value.", "unit": "", "color": "#cccccc", "plot": False},
]

ARDUPILOT_RAW_LOG_PARAMS = [
    {"name": "Attitude EKF Active", "param": "Attitude EKF Active", "desc": "ATT.AEKF reports which EKF attitude solution is active for the attitude estimate at this point in the log.", "unit": "", "color": "#ffffff", "plot": False},
    {"name": "Command Frame", "param": "CMD_Frame", "desc": "Mission command coordinate frame from CMD.Frame, such as global, relative-altitude, terrain, or local frames used to interpret command position fields.", "unit": "", "color": "#cccccc", "plot": False},

    # Plane/QuadPlane CTUN fields
    {"name": "Plane Airspeed", "param": "CTUN_As", "desc": "Plane control-tuning airspeed estimate from CTUN.As. Uses the airspeed sensor when healthy, otherwise ArduPilot may use a synthetic estimate.", "unit": "m/s", "color": "#ffffff", "plot": False},
    {"name": "Plane Synthetic Airspeed", "param": "CTUN_SAs", "desc": "Synthetic or equivalent airspeed estimate from CTUN.SAs, useful when no healthy physical airspeed sensor is available.", "unit": "m/s", "color": "#cccccc", "plot": False},
    {"name": "Plane Airspeed Source", "param": "CTUN_AsT", "desc": "Airspeed source/type from CTUN.AsT: 0=no new estimate, 1=airspeed sensor, 2=DCM synthetic, 3=EKF3 synthetic, 4=simulation.", "unit": "", "color": "#dddddd", "plot": False},
    {"name": "Equivalent/True Airspeed Ratio", "param": "CTUN_E2T", "desc": "Equivalent-to-true airspeed ratio from CTUN.E2T. This helps interpret how indicated/equivalent airspeed relates to true airspeed at the current conditions.", "unit": "", "color": "#cccccc", "plot": False},
    {"name": "Groundspeed Undershoot", "param": "CTUN_GU", "desc": "Groundspeed undershoot from CTUN.GU in minimum-groundspeed control. Positive values indicate the aircraft is below the requested minimum groundspeed.", "unit": "cm/s", "color": "#ffaa00", "plot": False},
    {"name": "Plane Desired Roll", "param": "CTUN_NavRoll", "desc": "Desired roll angle from Plane navigation/control tuning (CTUN.NavRoll). Compare with CTUN.Roll to see how closely the aircraft follows roll commands.", "unit": "deg", "color": "#ff99ff", "plot": False},
    {"name": "Plane Actual Roll", "param": "CTUN_Roll", "desc": "Achieved roll angle from Plane control tuning (CTUN.Roll). This is the actual roll used for comparison with the desired navigation roll.", "unit": "deg", "color": "#ff00ff", "plot": False},
    {"name": "Plane Desired Pitch", "param": "CTUN_NavPitch", "desc": "Desired pitch angle from Plane navigation/control tuning (CTUN.NavPitch), with pitch trims already applied.", "unit": "deg", "color": "#99ffff", "plot": False},
    {"name": "Plane Actual Pitch", "param": "CTUN_Pitch", "desc": "Achieved pitch angle from Plane control tuning (CTUN.Pitch), with pitch trims already applied; zero is the trimmed level-flight attitude.", "unit": "deg", "color": "#00ffff", "plot": False},
    {"name": "Plane Rudder Output", "param": "CTUN_RdO", "desc": "Scaled rudder output from Plane control tuning (CTUN.RdO). Use it to see how much yaw/rudder command the controller is sending.", "unit": "", "color": "#ffff99", "plot": False},
    {"name": "Plane Rudder Output", "param": "CTUN_RdrOut", "desc": "Scaled rudder output from Plane control tuning (CTUN.RdrOut). Use it to see how much yaw/rudder command the controller is sending.", "unit": "", "color": "#ffff99", "plot": False},

    # QuadPlane tuning fields that may remain under their raw QTUN names
    {"name": "Quad Control Altitude", "param": "QTUN_Alt", "desc": "QuadPlane vertical-flight altitude estimate from QTUN.Alt. Compare with QTUN_DAlt/Desired Altitude (Quad) during hover, QLOITER, QRTL, or QLAND.", "unit": "m", "color": "#00ff00", "plot": False},
    {"name": "Quad Climb Rate", "param": "QTUN_CRt", "desc": "QuadPlane vertical-flight climb rate from QTUN.CRt. Positive and negative values show climb or descent while using quad motors.", "unit": "cm/s", "color": "#00ccaa", "plot": False},

    # Plane NTUN fields
    {"name": "Target Latitude", "param": "NTUN_TLat", "desc": "Navigation target latitude from NTUN.TLat. This is the waypoint, loiter target, or intermediate target the controller is steering toward.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "Target Longitude", "param": "NTUN_TLng", "desc": "Navigation target longitude from NTUN.TLng. This is the waypoint, loiter target, or intermediate target the controller is steering toward.", "unit": "deg", "color": "#ffffff", "plot": False},
    {"name": "Airspeed Error", "param": "NTUN_AsE", "desc": "Airspeed error from NTUN.AsE, showing the difference between the aircraft's current airspeed and the desired target airspeed.", "unit": "m/s", "color": "#ffaa00", "plot": False},

    # GPS accuracy/performance fields not renamed by the parser
    {"name": "GPS Yaw Accuracy", "param": "GPA_YAcc", "desc": "GPS yaw accuracy from GPA.YAcc when a GPS yaw/heading-capable receiver is present. Lower values indicate a more precise GPS-derived heading.", "unit": "deg", "color": "#ffaa00", "plot": False},
    {"name": "PM Error Line", "param": "PM_ErrL", "desc": "Performance-monitoring error-line field from PM.ErrL, logged by ArduPilot when scheduler/performance diagnostics record an internal error location.", "unit": "", "color": "#ff7777", "plot": False},
    {"name": "PM Error Count", "param": "PM_ErrC", "desc": "Performance-monitoring error count from PM.ErrC. Non-zero values indicate scheduler/performance errors were recorded in this PM sample.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "PM Error Count", "param": "PM_ErC", "desc": "Performance-monitoring error count from older PM.ErC logs. Non-zero values indicate scheduler/performance errors were recorded in this PM sample.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "PM Internal Errors", "param": "PM_IntE", "desc": "Internal error bitmask/count from PM.IntE. Use this as a warning indicator for firmware-level internal errors during the log.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "PM Internal Errors", "param": "PM_InE", "desc": "Internal error bitmask/count from older PM.InE logs. Use this as a warning indicator for firmware-level internal errors during the log.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "SPI Error Count", "param": "PM_SPIC", "desc": "SPI bus error count from PM.SPIC. Increasing values can indicate sensor-bus communication problems.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "I2C Error Count", "param": "PM_I2CC", "desc": "I2C bus error count from PM.I2CC. Increasing values can indicate peripheral or sensor-bus communication problems.", "unit": "", "color": "#ff5555", "plot": False},
    {"name": "I2C Isr Count", "param": "PM_I2CI", "desc": "I2C interrupt/service count from PM.I2CI, mainly useful for low-level diagnostics of I2C bus activity.", "unit": "", "color": "#cccccc", "plot": False},
]

ARDUPILOT_OUTPUT_EXTENSION_PARAMS = [
    *[
        {"name": f"Raw Output {i}", "param": f"rcou_C{i}", "desc": f"Raw PWM command in microseconds sent to ArduPilot physical output channel {i}. This appears when the channel is not classified as a motor or control-surface servo.", "unit": "us", "color": "#cccccc", "plot": False}
        for i in range(1, 33)
    ],
    *[
        {"name": f"Output {i + 1} (M{i + 1})", "param": f"motor[{i}]", "desc": f"PWM output for ArduPilot motor function Motor{i + 1}.", "unit": "us", "color": "#ffaa00" if i % 2 == 0 else "#ff5500", "plot": False}
        for i in range(16, 32)
    ],
    *[
        {"name": f"Servo {i + 1} Out", "param": f"servo[{i}]", "desc": f"PWM output for ArduPilot output channel {i + 1} when mapped as a servo/control surface.", "unit": "us", "color": "#888888" if i % 2 == 0 else "#444444", "plot": False}
        for i in range(16, 32)
    ],
]

ARDUPILOT_PARAMS.extend(ARDUPILOT_EXTRA_PARAMS)
ARDUPILOT_PARAMS.extend(ARDUPILOT_CAM_CMD_PARAMS)
ARDUPILOT_PARAMS.extend(ARDUPILOT_RAW_LOG_PARAMS)
ARDUPILOT_PARAMS.extend(ARDUPILOT_OUTPUT_EXTENSION_PARAMS)

ARDUPILOT_DESC_OVERRIDES = {
    "pos_z": "Relative height used by the 3D view, in metres. It is calculated from the ArduPilot position estimate so the flight path starts near zero rather than at GPS altitude above sea level.",
    "attitude[0]": "Actual aircraft roll angle in degrees from ATT.Roll. Negative is left wing down; positive is right wing down.",
    "attitude[1]": "Actual aircraft pitch angle in degrees from ATT.Pitch. Negative is nose down/forward; positive is nose up/back.",
    "attitude[2]": "Actual heading/yaw in degrees from ATT.Yaw, where 0 is north and values wrap through 360.",
    "Desired Roll": "Target roll angle in degrees from ATT.DesRoll. Compare with Roll Angle to see how closely the aircraft follows the requested bank.",
    "Desired Pitch": "Target pitch angle in degrees from ATT.DesPitch. Compare with Pitch Angle to see pitch-tracking error.",
    "Desired Yaw": "Target heading in degrees from ATT.DesYaw. Compare with Yaw to see heading-tracking error.",
    "Desired Altitude (Copter)": "Copter altitude target from CTUN.DAlt during altitude-controlled modes such as AltHold, Loiter, RTL, or Auto.",
    "Desired Altitude (Quad)": "QuadPlane vertical-flight altitude target from QTUN.DAlt, used in quad/VTOL modes such as QHOVER, QLOITER, QRTL, and QLAND.",
    "vbat (V)": "Main battery voltage from BAT.Volt. Watch for sag under throttle and recovery when load is reduced.",
    "amperage (A)": "Instantaneous battery current draw from BAT.Curr in amps. Useful for spotting high-load manoeuvres or power-system stress.",
    "energyCumulative (mAh)": "Cumulative battery capacity consumed from BAT.CurrTot, in milliamp-hours since the log began.",
    "batteryRemaining": "Battery remaining percentage from BAT.RemPct when the battery monitor can estimate remaining capacity.",
    "GPS_coord[0]": "GPS latitude from GPS.Lat in degrees. This is used for map placement and ground-track bounds.",
    "GPS_coord[1]": "GPS longitude from GPS.Lng in degrees. This is used for map placement and ground-track bounds.",
    "GPS_numSat": "Number of satellites used by the GPS solution from GPS.NSats. Low values usually mean weak or unreliable positioning.",
    "GPS_speed (m/s)": "Horizontal ground speed from GPS.Spd in metres per second.",
    "GPS_ground_course": "Course over ground from GPS.GCrs in degrees, where 0 is north. This is direction of travel, not necessarily aircraft nose heading.",
    "GPS_altitude": "GPS altitude above mean sea level from GPS.Alt. ArduPilot generally relies more on EKF/barometer altitude for control.",
    "GPS_hdop": "Horizontal dilution of precision from GPS.HDop. Lower is better; around 1.5 is good and above about 2.0 is less desirable.",
    "GPS_VZ": "GPS vertical velocity from GPS.VZ. This is climb/descent rate reported by the GPS receiver, separate from barometer/EKF climb rate.",
    "POS_Lat": "EKF fused latitude estimate from POS.Lat. This is the navigation solution after ArduPilot combines sensors such as GPS, barometer, and IMU.",
    "POS_Lng": "EKF fused longitude estimate from POS.Lng. This is the navigation solution after ArduPilot combines sensors such as GPS, barometer, and IMU.",
    "POS_Alt": "EKF fused altitude above mean sea level from POS.Alt.",
    "POS_RelHomeAlt": "EKF altitude relative to home from POS.RelHomeAlt. This is usually the most intuitive altitude-above-takeoff value.",
    "POS_RelOriginAlt": "EKF altitude relative to the EKF origin from POS.RelOriginAlt, useful when the EKF origin differs from home.",
    "Throttle (Commanded)": "TECS throttle command from TECS.thr for fixed-wing energy control. It is the controller-requested throttle before output mixing.",
    "TECS Altitude": "Altitude estimate used by TECS from TECS.h for fixed-wing speed/height energy management.",
    "TECS Desired Alt": "Target altitude used by TECS from TECS.h_dem.",
    "TECS Airspeed": "Airspeed used by TECS from TECS.v for fixed-wing energy management.",
    "TECS Desired Airspeed": "Target airspeed requested by TECS from TECS.v_dem.",
    "TECS Desired Pitch": "Pitch demand from TECS.ptch used to manage fixed-wing speed and height.",
    "Throttle Out (Copter)": "Final copter throttle output from CTUN.ThO, normally on a 0-1000 scale in ArduPilot logs.",
    "Throttle Out (Quad)": "Final QuadPlane vertical motor throttle output from QTUN.ThO during quad/VTOL flight.",
    "IMUTemperature": "Primary IMU temperature from IMU.T. Temperature changes can affect sensor bias and vibration analysis.",
    "Temp": "Battery monitor temperature from BAT.Temp when available. Not all power modules provide this value.",
    "BaroAlt (cm)": "Barometer altitude from BARO.Alt converted into centimetres for compatibility with the existing viewer units.",
    "gyroADC[0]": "Gyro X-axis rotation rate from IMU.GyrX in radians per second; roughly roll-rate motion.",
    "gyroADC[1]": "Gyro Y-axis rotation rate from IMU.GyrY in radians per second; roughly pitch-rate motion.",
    "gyroADC[2]": "Gyro Z-axis rotation rate from IMU.GyrZ in radians per second; roughly yaw-rate motion.",
    "accSmooth[0]": "IMU X-axis acceleration from IMU.AccX, scaled internally to the viewer's 2048 LSB/G convention for shared acceleration stats.",
    "accSmooth[1]": "IMU Y-axis acceleration from IMU.AccY, scaled internally to the viewer's 2048 LSB/G convention for shared acceleration stats.",
    "accSmooth[2]": "IMU Z-axis acceleration from IMU.AccZ, scaled internally to the viewer's 2048 LSB/G convention for shared acceleration stats.",
    "magADC[0]": "Compass magnetic field X-axis value from MAG.MagX after calibration offsets are applied.",
    "magADC[1]": "Compass magnetic field Y-axis value from MAG.MagY after calibration offsets are applied.",
    "magADC[2]": "Compass magnetic field Z-axis value from MAG.MagZ after calibration offsets are applied.",
    "vibeX": "Vibration level on the X axis from VIBE.VibeX. High values can indicate prop, motor, mounting, or frame vibration problems.",
    "vibeY": "Vibration level on the Y axis from VIBE.VibeY. High values can indicate prop, motor, mounting, or frame vibration problems.",
    "vibeZ": "Vibration level on the Z axis from VIBE.VibeZ. High values can affect altitude and attitude estimation.",
    "isFlying": "ArduPilot landed-state flag from STAT.isFlying. A value of 1 means the vehicle is considered airborne by the flight stack.",
    "Armed": "Arming state from STAT.Armed. A value of 1 means outputs are armed; 0 means disarmed.",
    "Mode": "Active ArduPilot flight mode name, such as MANUAL, FBWA, AUTO, QHOVER, QLOITER, or RTL.",
    "ModeNum": "Numeric flight-mode identifier from MODE.ModeNum. The meaning depends on vehicle type, so the text Mode field is usually easier to read.",
    "stateFlags (flags)": "Human-readable arming state derived for the viewer, currently ARMED or DISARMED.",
    "EventId": "ArduPilot event ID from EV.Id, used for events such as arming, disarming, home set, land complete, failsafes, and other state changes.",
    "Attitude Err Roll/Pitch": "Average roll/pitch attitude estimate error from ATT.ErrRP. Values closer to zero indicate better attitude-estimator agreement.",
    "Attitude Err Yaw": "Average yaw attitude estimate error from ATT.ErrYaw. Values closer to zero indicate better heading-estimator agreement.",
    "GPS_week": "GPS week number from GPS.GWk. Usually only useful when correlating log time with absolute GPS time.",
    "Mag Health": "Compass health flag from MAG.Health. A false/zero value indicates ArduPilot considered that compass unhealthy.",
    "Throttle In (Copter)": "Pilot throttle input from CTUN.ThI on ArduPilot's 0-1000 throttle scale.",
    "Throttle Hover (Copter)": "Estimated throttle needed to hover from CTUN.ThH, usually in the 0.0-1.0 range.",
    "Throttle Desired (Copter)": "Desired throttle from CTUN.ThD before final output limiting/mixing.",
    "Control Altitude (Copter)": "Current EKF altitude used by copter altitude control from CTUN.Alt.",
    "Baro Altitude (Copter)": "Barometer altitude above ground from CTUN.BAlt, useful for comparing baro altitude with EKF or rangefinder altitude.",
    "Terrain Altitude (Copter)": "Terrain altitude estimate from CTUN.TAlt when terrain data/range sources are available.",
    "Desired Climb Rate (Copter)": "Desired climb or descent rate from CTUN.DCRt in centimetres per second.",
    "Climb Rate (Copter)": "Actual climb or descent rate from CTUN.CRt in centimetres per second.",
    "Altitude Error": "Difference between current aircraft height and target height from NTUN.AltE.",
    "GPS Speed Accuracy": "GPS receiver's reported speed accuracy from GPA.SAcc. Lower values mean the GPS speed estimate is more precise.",
    "PM Free Memory": "Available autopilot memory from PM.Mem in bytes. Very low free memory can point to resource pressure.",
    "PM CPU Load": "Scheduler CPU load from PM.Load, reported as percentage times ten by ArduPilot.",
    "AutoTune Axis": "Axis currently being tuned by AutoTune from ATUN.Axis; typically roll or pitch depending on vehicle and firmware.",
    "AutoTune Step": "AutoTune state from ATUN.TuneStep: returning to level, testing a response, or updating gains.",
    "CMD_CId": "MAVLink mission command ID from CMD.CId, identifying the command type such as waypoint, loiter, takeoff, or land.",
}

for i in range(32):
    ARDUPILOT_DESC_OVERRIDES[f"motor[{i}]"] = (
        f"PWM command in microseconds for ArduPilot Motor{i + 1} when a SERVOn_FUNCTION is mapped to that motor. "
        "Use this to inspect motor/throttle output sent by the flight controller."
    )
    ARDUPILOT_DESC_OVERRIDES[f"servo[{i}]"] = (
        f"PWM command in microseconds for physical output channel {i + 1} when it is mapped as a servo, tilt, gimbal, or control-surface output. "
        "Use the vehicle's SERVOn_FUNCTION settings to identify the connected surface or mechanism."
    )

RC_CHANNEL_DESCS = {
    0: "Pilot roll stick input from RCIN.C1 in microseconds, typically around 1000-2000 us.",
    1: "Pilot pitch stick input from RCIN.C2 in microseconds, typically around 1000-2000 us.",
    2: "Pilot yaw/rudder stick input from RCIN.C4 in microseconds, typically around 1000-2000 us.",
    3: "Pilot throttle stick input from RCIN.C3 in microseconds, typically around 1000-2000 us.",
}
for i in range(16):
    ARDUPILOT_DESC_OVERRIDES[f"rcData[{i}]"] = RC_CHANNEL_DESCS.get(
        i,
        f"Auxiliary RC input channel {i + 1} from RCIN.C{i + 1} in microseconds. This may be a mode switch, tuning knob, camera control, or other user-assigned input.",
    )

for p in ARDUPILOT_PARAMS:
    if p["param"] in ARDUPILOT_DESC_OVERRIDES:
        p["desc"] = ARDUPILOT_DESC_OVERRIDES[p["param"]]


EDGETX_PARAMS = [
    # Core Attitude & Position
    {"name": "Altitude (GPS)", "param": "GPS_altitude", "desc": "Altitude above sea level or takeoff point reported by GPS.", "unit": "m", "color": "#00ff00", "plot": True, "trail": True},
    {"name": "Altitude (Baro)", "param": "BaroAlt (cm)", "desc": "Altitude measured by the barometer sensor.", "unit": "m", "color": "#00ff88", "plot": False, "trail": False},
    {"name": "Roll Angle", "param": "attitude[0]", "desc": "Aircraft lean angle on the roll axis.", "unit": "deg", "color": "#ff00ff", "plot": True, "trail": True},
    {"name": "Pitch Angle", "param": "attitude[1]", "desc": "Aircraft tilt angle on the pitch axis.", "unit": "deg", "color": "#00ffff", "plot": True, "trail": True},
    {"name": "Yaw (Heading)", "param": "attitude[2]", "desc": "Aircraft heading relative to North.", "unit": "deg", "color": "#ffff00", "plot": True, "trail": False},
    
    # Power System
    {"name": "Battery Voltage", "param": "vbat (V)", "desc": "Main flight battery voltage reported by telemetry.", "unit": "V", "color": "#ffff00", "plot": True, "trail": True},
    {"name": "Current Draw", "param": "amperage (A)", "desc": "Real-time current draw from the battery.", "unit": "A", "color": "#ff3333", "plot": True, "trail": True},
    {"name": "Capacity Used", "param": "energyCumulative (mAh)", "desc": "Total battery capacity consumed.", "unit": "mAh", "color": "#ff6666", "plot": False, "trail": False},
    {"name": "Battery %", "param": "batteryRemaining", "desc": "Estimated battery percentage remaining.", "unit": "%", "color": "#aaff00", "plot": False, "trail": False},
    
    # GPS & Navigation
    {"name": "GPS Satellites", "param": "GPS_numSat", "desc": "Number of satellites locked.", "unit": "", "color": "#ffffff", "plot": True, "trail": True},
    {"name": "GPS Ground Speed", "param": "GPS_speed (m/s)", "desc": "Speed over ground measured by GPS.", "unit": "m/s", "color": "#00ffff", "plot": False, "trail": True},
    {"name": "GPS Course", "param": "GPS_ground_course", "desc": "Actual direction of travel over ground.", "unit": "deg", "color": "#ffff00", "plot": False, "trail": False},
    
    # Radio & Telemetry
    {"name": "RSSI", "param": "rssi", "desc": "Received Signal Strength Indicator at the receiver.", "unit": "dB", "color": "#ffffff", "plot": True, "trail": True},
    {"name": "Link Quality", "param": "linkQuality", "desc": "Link quality percentage.", "unit": "%", "color": "#00ff00", "plot": False, "trail": False},
    {"name": "TX RSSI", "param": "rssi_tx", "desc": "Telemetry Signal Strength at the transmitter.", "unit": "dB", "color": "#aaaaff", "plot": False, "trail": False},
    {"name": "TX Battery", "param": "TxBat(V)", "desc": "Radio transmitter battery voltage.", "unit": "V", "color": "#888888", "plot": False},

    # RC Inputs
    {"name": "Roll Stick", "param": "rcData[0]", "desc": "Aileron stick position.", "unit": "us", "color": "#ff00ff", "plot": False},
    {"name": "Pitch Stick", "param": "rcData[1]", "desc": "Elevator stick position.", "unit": "us", "color": "#00ffff", "plot": False},
    {"name": "Yaw Stick", "param": "rcData[2]", "desc": "Rudder stick position.", "unit": "us", "color": "#ffff00", "plot": False},
    {"name": "Throttle Stick", "param": "rcData[3]", "desc": "Throttle stick position.", "unit": "us", "color": "#ffffff", "plot": False},

    # System Status
    {"name": "Flight Mode", "param": "flightModeFlags (flags)", "desc": "Active flight mode (numeric index from EdgeTX).", "unit": "", "color": "#ffffff", "plot": False, "can_plot": False},
]

GPX_PARAMS = [
    # Core Attitude & Position
    {"name": "Altitude (Rel)", "param": "pos_z", "desc": "Relative altitude from the start point.", "unit": "m", "color": "#00ff00", "plot": True, "trail": True},
    {"name": "Altitude (MSL)", "param": "altitude_m", "desc": "Absolute altitude above Mean Sea Level.", "unit": "m", "color": "#00ffaa", "plot": True, "trail": False},
    {"name": "Speed", "param": "GPS_speed (m/s)", "desc": "Smoothed running or walking speed over ground.", "unit": "m/s", "color": "#00ffff", "plot": True, "trail": True},
    {"name": "Pace", "param": "pace (min/km)", "desc": "Current pace in minutes per kilometer or mile.", "unit": "min/km", "color": "#ffaa00", "plot": True, "trail": True},
    {"name": "Grade-Adjusted Pace", "param": "GAP (min/km)", "desc": "Pace adjusted for uphill/downhill slope to reflect equivalent flat-ground effort.", "unit": "min/km", "color": "#ff5500", "plot": True, "trail": True},
    {"name": "Slope", "param": "slope (%)", "desc": "Smoothed physical slope or grade (%). Positive for uphill, negative for downhill.", "unit": "%", "color": "#ff00ff", "plot": False, "trail": True},
    {"name": "Heart Rate", "param": "heart_rate", "desc": "Heart rate in beats per minute (bpm).", "unit": "bpm", "color": "#ff3333", "plot": True, "trail": True},
    {"name": "Cadence", "param": "cadence", "desc": "Running cadence in steps per minute (spm) or cycling cadence in rpm.", "unit": "spm", "color": "#ffff00", "plot": True, "trail": True},
    {"name": "Stride Length", "param": "stride_length (m)", "desc": "Estimated horizontal stride length.", "unit": "m", "color": "#aaff00", "plot": False, "trail": False},
    {"name": "Climb Rate", "param": "climb_rate (m/min)", "desc": "Vertical ascent/descent rate (vario).", "unit": "m/min", "color": "#00aaff", "plot": False, "trail": False},
    {"name": "Cumulative Distance", "param": "distance_m", "desc": "Total cumulative distance covered.", "unit": "m", "color": "#ffaa55", "plot": True, "trail": False},
    {"name": "Cumulative Height Gain", "param": "cumulative_gain_m", "desc": "Total positive elevation climbed.", "unit": "m", "color": "#aaffaa", "plot": True, "trail": False},
]

def enrich_params(params_list, mappings=ENCODED_PARAMS):
    for p in params_list:
        if p['param'] in mappings:
            mapping = mappings[p['param']]
            p['mapping'] = mapping
            # Add values to description
            val_str = ", ".join([f"{k}={v}" for k, v in mapping.items()])
            p['desc'] = f"{p['desc']} Values: {val_str}"

enrich_params(INAV_PARAMS)
enrich_params(ARDUPILOT_PARAMS, ARDUPILOT_ENCODED_PARAMS)
enrich_params(EDGETX_PARAMS)
enrich_params(GPX_PARAMS)

