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

try:
    from PyQt6.QtWidgets import QApplication, QLabel
    print("PyQt6 imported successfully")
except ImportError as e:
    print(f"PyQt6 import failed: {e}")

try:
    import pyvista as pv
    print("pyvista imported successfully")
except ImportError as e:
    print(f"pyvista import failed: {e}")

try:
    from pyvistaqt import BackgroundPlotter
    print("pyvistaqt imported successfully")
except ImportError as e:
    print(f"pyvistaqt import failed: {e}")

try:
    import matplotlib
    print("matplotlib imported successfully")
except ImportError as e:
    print(f"matplotlib import failed: {e}")

try:
    import pygame
    print("pygame imported successfully")
except ImportError as e:
    print(f"pygame import failed: {e}")

try:
    import pandas as pd
    import numpy as np
    print("pandas and numpy imported successfully")
except ImportError as e:
    print(f"pandas or numpy import failed: {e}")

print("\nEnvironment setup complete.")
