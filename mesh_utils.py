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

def create_runner_mesh():
    """
    Creates a simple programmatic runner mesh using PyVista primitives.
    """
    scale = 2.5
    # Head: Sphere
    head = pv.Sphere(radius=0.15 * scale, center=(0, 0, 1.2 * scale))
    
    # Torso: Cylinder
    torso = pv.Cylinder(center=(0, 0, 0.7 * scale), direction=(0, 0, 1), radius=0.1 * scale, height=0.7 * scale)
    
    # Left Leg: Cylinder
    l_leg = pv.Cylinder(center=(-0.15 * scale, 0, 0.22 * scale), direction=(0, 0, 1), radius=0.04 * scale, height=0.44 * scale)
    
    # Right Leg: Cylinder
    r_leg = pv.Cylinder(center=(0.15 * scale, 0, 0.22 * scale), direction=(0, 0, 1), radius=0.04 * scale, height=0.44 * scale)
    
    # Left Arm: Cylinder (angled slightly forward)
    l_arm = pv.Cylinder(center=(-0.25 * scale, 0.1 * scale, 0.8 * scale), direction=(0, 0.5, 1), radius=0.03 * scale, height=0.3 * scale)
    
    # Right Arm: Cylinder (angled slightly backward)
    r_arm = pv.Cylinder(center=(0.25 * scale, -0.1 * scale, 0.8 * scale), direction=(0, -0.5, 1), radius=0.03 * scale, height=0.3 * scale)
    
    # Combine all parts
    mesh = head + torso + l_leg + r_leg + l_arm + r_arm
    mesh.cell_data["colors"] = np.ones(mesh.n_cells)
    
    return mesh


if __name__ == "__main__":
    # Test visualization
    aircraft = create_aircraft_mesh()
    plotter = pv.Plotter()
    plotter.add_mesh(aircraft, color="lightblue", show_edges=True)
    plotter.show_axes()
    plotter.show()
