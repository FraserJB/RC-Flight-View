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

import pyvista as pv
import numpy as np

def create_aircraft_mesh():
    """
    Creates a simple programmatic aircraft mesh using PyVista primitives.
    """
    scale = 5.0
    # Fuselage: Cylinder
    fuselage = pv.Cylinder(center=(0, 0, 0), direction=(1, 0, 0), radius=0.1 * scale, height=1.0 * scale)
    
    # Nose: Cone
    nose = pv.Cone(center=(0.55 * scale, 0, 0), direction=(1, 0, 0), radius=0.1 * scale, height=0.2 * scale)
    
    # Wings: Box (thin and wide)
    wings = pv.Box(bounds=(-0.1 * scale, 0.1 * scale, -0.8 * scale, 0.8 * scale, -0.02 * scale, 0.02 * scale))
    wings.translate((0, 0, 0), inplace=True)
    
    # Vertical Tail: Box
    v_tail = pv.Box(bounds=(-0.45 * scale, -0.3 * scale, -0.01 * scale, 0.01 * scale, 0, 0.2 * scale))
    
    # Horizontal Tail: Box
    h_tail = pv.Box(bounds=(-0.45 * scale, -0.3 * scale, -0.25 * scale, 0.25 * scale, -0.01 * scale, 0.01 * scale))
    
    # Combine all parts
    mesh = fuselage + nose + wings + v_tail + h_tail
    
    # Color the mesh
    mesh.cell_data["colors"] = np.ones(mesh.n_cells)
    
    return mesh

if __name__ == "__main__":
    # Test visualization
    aircraft = create_aircraft_mesh()
    plotter = pv.Plotter()
    plotter.add_mesh(aircraft, color="lightblue", show_edges=True)
    plotter.show_axes()
    plotter.show()
