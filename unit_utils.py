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

import pandas as pd
import numpy as np

DEFAULT_UNITS = {
    "Distance": "m",
    "Height": "m",
    "Speed": "mph",
    "Temperature": "C"
}

def get_unit_category(param_name, base_unit):
    # Determine the category of a parameter based on its name and base unit
    if base_unit == "cm":
        if "EPV" in param_name or "navPos[2]" in param_name:
            return "Height"
        elif "EPH" in param_name or "navPos" in param_name:
            return "Distance"
            
    if param_name in ["pos_z", "GPS_altitude", "Altitude (Rel)", "GPS Altitude (MSL)"] or "Altitude" in param_name:
        return "Height"
        
    if param_name in ["pos_x", "pos_y", "distance_to_home"] or "Distance" in param_name:
        return "Distance"
        
    if "Temp" in param_name:
        return "Temperature"
        
    if base_unit == "m/s" or "Speed" in param_name or "Wind" in param_name:
        return "Speed"
        
    return None

def convert_value(val, category, current_unit, target_unit):
    # Normalise units (sometimes "°C" vs "C")
    if current_unit == "°C": current_unit = "C"
    if target_unit == "°C": target_unit = "C"
    
    if current_unit == target_unit:
        return val, target_unit
        
    if category == "Distance" or category == "Height":
        # Convert everything to meters first
        m_val = val
        if current_unit == "cm":
            m_val = val / 100.0
        elif current_unit == "ft":
            m_val = val * 0.3048
        elif current_unit == "km":
            m_val = val * 1000.0
        elif current_unit == "miles":
            m_val = val * 1609.34
            
        # Convert meters to target
        if target_unit == "m": return m_val, "m"
        elif target_unit == "ft": return m_val / 0.3048, "ft"
        elif target_unit == "km": return m_val / 1000.0, "km"
        elif target_unit == "miles": return m_val / 1609.34, "miles"
        
    elif category == "Speed":
        # Convert everything to m/s first
        ms_val = val
        if current_unit == "km/h":
            ms_val = val / 3.6
        elif current_unit == "mph":
            ms_val = val * 0.44704
            
        # Convert m/s to target
        if target_unit == "m/s": return ms_val, "m/s"
        elif target_unit == "km/h": return ms_val * 3.6, "km/h"
        elif target_unit == "mph": return ms_val / 0.44704, "mph"
        
    elif category == "Temperature":
        if current_unit == "C" and target_unit == "F":
            return (val * 9/5) + 32, "F"
        elif current_unit == "F" and target_unit == "C":
            return (val - 32) * 5/9, "C"
            
    return val, current_unit

def apply_units_to_df(df_raw, param_config, unit_prefs):
    """
    Returns a new dataframe with converted units, and a new param_config list
    with updated unit strings.
    """
    if df_raw is None:
        return None, param_config
        
    df = df_raw.copy()
    new_config = []
    converted_cols = set()
    
    for p in param_config:
        new_p = p.copy()
        col = new_p['param']
        
        # Persist the original base unit to prevent repeated conversion corruption
        if 'base_unit' not in new_p:
            new_p['base_unit'] = new_p.get('unit', '').replace('°C', 'C')
        base_unit = new_p['base_unit']
        
        category = get_unit_category(new_p['name'], base_unit) or get_unit_category(col, base_unit)
        
        if category and category in unit_prefs:
            target_unit = unit_prefs[category]
            if col in df.columns and col not in converted_cols:
                converted_series, actual_unit = convert_value(df[col], category, base_unit, target_unit)
                df[col] = converted_series
                if category == "Temperature" and actual_unit in ["C", "F"]:
                    new_p['unit'] = f"°{actual_unit}"
                else:
                    new_p['unit'] = actual_unit
                converted_cols.add(col)
            else:
                if category == "Temperature" and target_unit in ["C", "F"]:
                    new_p['unit'] = f"°{target_unit}"
                else:
                    new_p['unit'] = target_unit
        new_config.append(new_p)
        
    # Fallback: ensure pos_x, pos_y, pos_z are converted even if not in param_config
    for col in ['pos_x', 'pos_y', 'pos_z']:
        if col in df.columns and col not in converted_cols:
            base_unit = 'm'
            category = "Distance" if col in ['pos_x', 'pos_y'] else "Height"
            if category in unit_prefs:
                target_unit = unit_prefs[category]
                if base_unit != target_unit:
                    converted_series, _ = convert_value(df[col], category, base_unit, target_unit)
                    df[col] = converted_series
                    converted_cols.add(col)
                    
    return df, new_config
