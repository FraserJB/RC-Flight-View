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
import hashlib
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, QEvent, Qt, QTimer
import numpy as np
from PIL import Image, ImageEnhance
from mesh_utils import create_aircraft_mesh

class Viewer3D(QWidget):
    pathPointClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter)
        
        self.aircraft_mesh = create_aircraft_mesh()
        self.aircraft_actor = self.plotter.add_mesh(self.aircraft_mesh, color="lightblue", name="aircraft")
        
        self.path_actor = None
        self.map_actor = None
        self.terrain_actor = None
        self.ghost_actor = None
        
        # FPV-specific actors for independent properties
        self.fpv_map_actor = None
        self.fpv_path_actor = None
        self.fpv_ghost_actor = None
        
        self.full_path_points = None
        self.ghost_points = []
        
        self.map_visible = True
        self.map_opacity = 1.0
        self.ghost_visible = True
        
        # FPV state
        self.fpv_active = False
        self.fpv_renderer = None
        self.fpv_border = None
        
        # Setup plotter
        self.plotter.set_background("#1e1e1e") # Darker gray
        self.plotter.add_axes(line_width=2, labels_off=False)
        self.plotter.view_isometric()
        
        # Add a small takeoff marker
        takeoff_marker = pv.Sphere(radius=1.0, center=(0, 0, 0))
        self.plotter.add_mesh(takeoff_marker, color="red", name="takeoff")
        
        self.dist_unit = "m"
        self.height_unit = "m"
        self._refresh_grid()
        self._click_press_pos = None
        self._click_drag_threshold_px = 5
        self.plotter.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.plotter:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._click_press_pos = event.position()
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                press_pos = self._click_press_pos
                self._click_press_pos = None
                if press_pos is not None:
                    release_pos = event.position()
                    delta = release_pos - press_pos
                    if (delta.x() * delta.x() + delta.y() * delta.y()) <= (self._click_drag_threshold_px ** 2):
                        x = float(release_pos.x())
                        y = float(release_pos.y())
                        QTimer.singleShot(0, lambda x=x, y=y: self._pick_path_at_screen_pos(x, y))

        return super().eventFilter(obj, event)

    def update_grid_units(self, dist_unit, height_unit):
        self.dist_unit = dist_unit
        self.height_unit = height_unit
        self._refresh_grid()

    def _refresh_grid(self):
        self.plotter.show_grid(color="#444444", 
                               xtitle=f"Downrange ({self.dist_unit})", 
                               ytitle=f"Crossrange ({self.dist_unit})", 
                               ztitle=f"Height ({self.height_unit})", 
                               font_size=10)

    @staticmethod
    def _clamp(value, min_value, max_value):
        return max(min_value, min(max_value, value))

    def _prepare_map_texture(self, texture_path):
        """Normalize bright/dark map textures so scene lighting cannot wash them out."""
        abs_path = os.path.abspath(texture_path)
        try:
            img = Image.open(abs_path).convert("RGB")
            arr = np.asarray(img, dtype=np.float32) / 255.0
            luminance = (arr[:, :, 0] * 0.2126) + (arr[:, :, 1] * 0.7152) + (arr[:, :, 2] * 0.0722)
            mean = float(np.mean(luminance))
            std = float(np.std(luminance))

            # Bring very bright street/topo maps down and lift very dark imagery
            # slightly, while preserving mid-tone satellite maps.
            if mean > 0.68:
                target_mean = 0.56
            elif mean < 0.32:
                target_mean = 0.40
            else:
                target_mean = mean

            brightness = Viewer3D._clamp(target_mean / max(mean, 0.01), 0.55, 1.35)
            contrast = Viewer3D._clamp(0.24 / max(std, 0.08), 1.0, 1.35)

            adjusted = ImageEnhance.Brightness(img).enhance(brightness)
            adjusted = ImageEnhance.Contrast(adjusted).enhance(contrast)

            cache_key = hashlib.md5(f"{abs_path}_{os.path.getmtime(abs_path):.6f}_{brightness:.3f}_{contrast:.3f}".encode()).hexdigest()[:10]
            out_path = os.path.join(os.path.dirname(abs_path), f"current_map_render_{cache_key}.jpg")
            adjusted.save(out_path, quality=92)
            return out_path
        except Exception:
            return abs_path

    def clear_display_data(self):
        """Remove log-specific 3D data while leaving the viewer controls intact."""
        for attr in ("path_actor", "map_actor", "terrain_actor", "ghost_actor"):
            actor = getattr(self, attr, None)
            if actor is not None:
                self.plotter.remove_actor(actor)
                setattr(self, attr, None)

        if self.fpv_renderer:
            for attr in ("fpv_path_actor", "fpv_map_actor", "fpv_ghost_actor"):
                actor = getattr(self, attr, None)
                if actor is not None:
                    self.fpv_renderer.RemoveActor(actor)
                    setattr(self, attr, None)

        self.full_path_points = None
        self.ghost_points = []
        self.breadcrumb_indices = []
        self.breadcrumb_indices_array = np.array([], dtype=int)
        self.current_idx = 0

        if self.aircraft_actor is not None:
            self.aircraft_actor.user_matrix = np.eye(4)

        self._refresh_grid()
        self.plotter.update()
        if self.fpv_renderer:
            self.fpv_renderer.Render()

    def set_path(self, points, reset_camera=True):
        """Sets the full flight path points (N, 3)."""
        self.full_path_points = points
        
        # Precompute breadcrumb indices for perfectly accurate trails
        self.breadcrumb_indices = [0]
        last_pos = points[0]
        for i, pos in enumerate(points):
            if np.linalg.norm(pos - last_pos) > 5.0:
                self.breadcrumb_indices.append(i)
                last_pos = pos
        self.breadcrumb_indices_array = np.array(self.breadcrumb_indices)

        if self.path_actor:
            self.plotter.remove_actor(self.path_actor)
        
        # Create a line mesh for the path
        self.path_mesh = pv.PolyData(points)
        cells = np.full((len(points)-1, 3), 2, dtype=np.int_)
        cells[:, 1] = np.arange(len(points)-1)
        cells[:, 2] = np.arange(1, len(points))
        self.path_mesh.lines = cells
        
        # Add default scalars (altitude)
        self.path_mesh.point_data["scalars"] = points[:, 2]
        
        self.path_actor = self.plotter.add_mesh(self.path_mesh, scalars="scalars", cmap="viridis", 
                                                line_width=4, name="path", render_lines_as_tubes=True,
                                                pickable=True,
                                                scalar_bar_args={'title': 'Altitude', 'fmt': '%.1f', 
                                                               'bold': True, 'shadow': False,
                                                               'label_font_size': 10, 'title_font_size': 12})
        
        if self.fpv_renderer:
            if self.fpv_path_actor:
                self.fpv_renderer.RemoveActor(self.fpv_path_actor)
            import vtk
            self.fpv_path_actor = vtk.vtkActor()
            self.fpv_path_actor.SetMapper(self.path_actor.GetMapper())
            self.fpv_path_actor.SetProperty(self.path_actor.GetProperty())
            self.fpv_renderer.AddActor(self.fpv_path_actor)
        
        if not reset_camera:
            old_cam = self.plotter.camera.copy()
            self._refresh_grid()
            self.plotter.camera = old_cam
        else:
            self._refresh_grid()
            self.plotter.reset_camera()
            self.plotter.view_isometric()

    def _pick_path_at_screen_pos(self, x, y):
        """Seek to the nearest path point when the flight path is clicked."""
        if self.full_path_points is None or self.path_actor is None:
            return

        try:
            import vtk

            renderer = self.plotter.iren.get_poked_renderer()
            if renderer is None:
                renderer = self.plotter.renderer

            try:
                scale = self.plotter._getPixelRatio()
            except Exception:
                scale = 1.0
            pick_x = int(round(x * scale))
            pick_y = int(round((self.plotter.height() - y - 1) * scale))

            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.025)
            picker.PickFromListOn()
            picker.AddPickList(self.path_actor)

            if not picker.Pick(pick_x, pick_y, 0, renderer):
                return

            picked = np.array(picker.GetPickPosition(), dtype=float)
            if not np.isfinite(picked).all():
                return

            points = np.asarray(self.full_path_points, dtype=float)
            if points.ndim != 2 or len(points) == 0:
                return

            deltas = points - picked
            dist_sq = np.einsum('ij,ij->i', deltas, deltas)
            if not np.isfinite(dist_sq).any():
                return

            idx = int(np.nanargmin(dist_sq))
            self.pathPointClicked.emit(idx)
        except Exception:
            return

    def update_path_scalars(self, scalars, label, unit=""):
        """Updates the coloring of the flight path based on new scalars."""
        if self.full_path_points is None:
            return
            
        self.path_mesh.point_data["scalars"] = scalars
        
        # Use integer format for motor outputs or satellite counts, otherwise 1 decimal
        fmt = '%.0f' if ('Motor' in label or 'Satellites' in label or 'RPM' in label) else '%.1f'
        
        # Include unit in title if provided
        title = f"{label} ({unit})" if unit else label
        
        # To update the color bar title, we need to re-add or access the scalar bar
        self.path_actor = self.plotter.add_mesh(self.path_mesh, scalars="scalars", cmap="viridis", 
                                                line_width=4, name="path", render_lines_as_tubes=True,
                                                reset_camera=False,
                                                pickable=True,
                                                scalar_bar_args={'title': title, 'fmt': fmt, 
                                                               'bold': True, 'shadow': False,
                                                               'label_font_size': 10, 'title_font_size': 12})
        if self.fpv_renderer:
            if self.fpv_path_actor:
                self.fpv_renderer.RemoveActor(self.fpv_path_actor)
            import vtk
            self.fpv_path_actor = vtk.vtkActor()
            self.fpv_path_actor.SetMapper(self.path_actor.GetMapper())
            self.fpv_path_actor.SetProperty(self.path_actor.GetProperty())
            self.fpv_renderer.AddActor(self.fpv_path_actor)
        self.plotter.update()

    def set_map(self, texture_path, bounds_xy, reset_camera=False):
        """
        Adds a ground plane with a satellite texture.
        bounds_xy: (min_x, max_x, min_y, max_y)
        """
        if self.map_actor:
            self.plotter.remove_actor(self.map_actor)
            self.map_actor = None
        if self.terrain_actor:
            self.plotter.remove_actor(self.terrain_actor)
            self.terrain_actor = None
            
        min_x, max_x, min_y, max_y = bounds_xy
        
        # Create a plane that covers the map bounds
        # We place it slightly below z=0 to avoid z-fighting with the path at takeoff
        plane = pv.Plane(
            center=((min_x + max_x)/2, (min_y + max_y)/2, -0.5),
            direction=(0, 0, 1),
            i_size=(max_x - min_x),
            j_size=(max_y - min_y)
        )
        
        # Explicitly generate texture coordinates
        plane.texture_map_to_plane(inplace=True)
        
        try:
            texture = pv.read_texture(self._prepare_map_texture(texture_path))
            # Render map textures unlit.  The image is normalized above, so OSM
            # stays readable and satellite imagery does not get crushed.
            self.map_actor = self.plotter.add_mesh(plane, texture=texture, name="map", 
                                                   lighting=False,
                                                   show_edges=False, opacity=self.map_opacity)
            self.map_actor.SetVisibility(self.map_visible)
            
            if self.fpv_renderer:
                if self.fpv_map_actor:
                    self.fpv_renderer.RemoveActor(self.fpv_map_actor)
                
                import vtk
                self.fpv_map_actor = vtk.vtkActor()
                self.fpv_map_actor.SetMapper(self.map_actor.GetMapper())
                self.fpv_map_actor.SetTexture(self.map_actor.GetTexture())
                # Copy properties but force 100% opacity for FPV
                self.fpv_map_actor.GetProperty().DeepCopy(self.map_actor.GetProperty())
                self.fpv_map_actor.GetProperty().SetOpacity(1.0)
                self.fpv_map_actor.GetProperty().SetAmbient(0.8)
                self.fpv_map_actor.GetProperty().SetDiffuse(0.2)
                self.fpv_renderer.AddActor(self.fpv_map_actor)
                self.fpv_map_actor.SetVisibility(self.map_visible)
            
            # Refresh grid and preserve camera if requested
            if not reset_camera:
                old_cam = self.plotter.camera.copy()
                self._refresh_grid()
                self.plotter.camera = old_cam
            else:
                self._refresh_grid()
                self.plotter.reset_camera()
                self.plotter.view_isometric()
        except Exception as e:
            print(f"Error loading map texture: {e}")

    def set_terrain(self, texture_path, elevations, x_grid, y_grid, reset_camera=False):
        """
        Adds a 3D terrain mesh with a satellite texture.
        elevations: 2D array of heights
        x_grid, y_grid: 2D arrays of X and Y local coordinates
        """
        if self.map_actor:
            self.plotter.remove_actor(self.map_actor)
            self.map_actor = None
        if self.terrain_actor:
            self.plotter.remove_actor(self.terrain_actor)
            self.terrain_actor = None
            
        elevations = np.asarray(elevations, dtype=float)
        x_grid = np.asarray(x_grid, dtype=float)
        y_grid = np.asarray(y_grid, dtype=float)
        if elevations.shape != x_grid.shape or elevations.shape != y_grid.shape:
            raise ValueError("Terrain elevation and coordinate grids must have matching shapes.")

        rows, cols = elevations.shape
        if rows < 2 or cols < 2:
            raise ValueError("Terrain grid must be at least 2x2.")

        # Build an explicit textured surface.  StructuredGrid texture mapping can
        # drift on non-planar terrain, so fixed UVs keep the map image locked to
        # the terrain corners.
        points = np.column_stack((
            x_grid.ravel(order='F'),
            y_grid.ravel(order='F'),
            elevations.ravel(order='F')
        ))

        faces = []
        for ix in range(cols - 1):
            for iy in range(rows - 1):
                p0 = ix * rows + iy
                p1 = (ix + 1) * rows + iy
                p2 = (ix + 1) * rows + (iy + 1)
                p3 = ix * rows + (iy + 1)
                faces.extend([4, p0, p1, p2, p3])

        terrain = pv.PolyData(points, np.array(faces))
        u = np.repeat(np.linspace(0.0, 1.0, cols), rows)
        v = np.tile(np.linspace(0.0, 1.0, rows), cols)
        terrain.active_texture_coordinates = np.column_stack((u, v))
        terrain = terrain.compute_normals(auto_orient_normals=True, inplace=False)
        
        try:
            # The textured map and bare terrain are separate actors.  This lets
            # "Show Map" hide the texture while leaving the terrain mesh visible.
            self.terrain_actor = self.plotter.add_mesh(
                terrain,
                color="#3a3a3a",
                name="terrain_mesh",
                lighting=True,
                ambient=0.35,
                diffuse=0.65,
                show_edges=True,
                edge_color="#5a5a5a",
                opacity=1.0
            )
            self.terrain_actor.SetVisibility(not self.map_visible)

            texture = pv.read_texture(self._prepare_map_texture(texture_path))
            # Keep texture colors stable; terrain shape remains visible through
            # geometry, path depth, and the separate mesh actor when the map is off.
            self.map_actor = self.plotter.add_mesh(terrain, texture=texture, name="map", 
                                                   lighting=False,
                                                   show_edges=False, opacity=self.map_opacity)
            self.map_actor.SetVisibility(self.map_visible)
            
            # Add a directional light from the side to create shadows on small hills
            # Check if we already have a scene light to avoid duplicates
            has_scene_light = any(
                hasattr(l, 'light_type') and str(l.light_type).lower() == 'scene light'
                for l in self.plotter.renderer.lights
            )
            if not has_scene_light:
                self.plotter.add_light(pv.Light(position=(0.5, 0.5, 1.0), 
                                                focal_point=(0, 0, 0), 
                                                intensity=1.0, 
                                                light_type='scene light'))
            if self.fpv_renderer:
                if self.fpv_map_actor:
                    self.fpv_renderer.RemoveActor(self.fpv_map_actor)
                import vtk
                self.fpv_map_actor = vtk.vtkActor()
                self.fpv_map_actor.SetMapper(self.map_actor.GetMapper())
                self.fpv_map_actor.SetTexture(self.map_actor.GetTexture())
                self.fpv_map_actor.GetProperty().DeepCopy(self.map_actor.GetProperty())
                self.fpv_map_actor.GetProperty().SetOpacity(1.0)
                self.fpv_map_actor.GetProperty().SetAmbient(0.8)
                self.fpv_map_actor.GetProperty().SetDiffuse(0.2)
                self.fpv_renderer.AddActor(self.fpv_map_actor)
                self.fpv_map_actor.SetVisibility(self.map_visible)
            if not reset_camera:
                old_cam = self.plotter.camera.copy()
                self._refresh_grid()
                self.plotter.camera = old_cam
            else:
                self._refresh_grid()
                self.plotter.reset_camera()
                self.plotter.view_isometric()
        except Exception as e:
            print(f"Error loading terrain texture: {e}")

    def update_aircraft(self, pos, attitude, idx):
        """
        Updates aircraft position and orientation.
        pos: (x, y, z)
        attitude: (roll, pitch, yaw) in degrees
        idx: current row index in dataframe
        """
        # Mesh forward is +X, Up is +Z
        roll, pitch, yaw = attitude
        angle_z = 90 - yaw
        
        # Apply rotations and translation
        transform = pv.Transform()
        transform.rotate_x(roll)
        transform.rotate_y(-pitch)
        transform.rotate_z(angle_z)
        transform.translate(pos)
        
        self.aircraft_actor.user_matrix = transform.matrix
        
        # Sync FPV Camera
        self.update_fpv_camera(pos, transform.matrix)
        
        # Ghost trail (breadcrumbs)
        self.current_idx = idx
        if self.ghost_visible:
            self._update_ghost_mesh()

    def _update_ghost_mesh(self):
        """Internal helper to regenerate the ghost breadcrumb trail actor."""
        if self.full_path_points is None or not hasattr(self, 'breadcrumb_indices_array'):
            return
            
        # Extract the exact path points up to the current index
        idx = getattr(self, 'current_idx', 0)
        valid_indices = self.breadcrumb_indices_array[self.breadcrumb_indices_array <= idx]
        
        if len(valid_indices) == 0:
            if getattr(self, 'ghost_actor', None) is not None:
                self.ghost_actor.SetVisibility(False)
            return
            
        pts = self.full_path_points[valid_indices]
        
        import vtk
        import pyvista as pv
        ghost_mesh = pv.PolyData(pts)
        
        if getattr(self, 'ghost_actor', None) is not None:
            # High-performance update: just swap the underlying VTK dataset on the mapper
            self.ghost_actor.GetMapper().SetInputData(ghost_mesh)
            self.ghost_actor.SetVisibility(self.ghost_visible)
            # FPV actor automatically inherits this change because they share the mapper!
        else:
            # First time creation
            self.ghost_actor = self.plotter.add_mesh(ghost_mesh, color="white", point_size=8, name="ghost", 
                                                    render_points_as_spheres=True, ambient=1.0, reset_camera=False)
            self.ghost_actor.SetVisibility(self.ghost_visible)
            
            if getattr(self, 'fpv_renderer', None) is not None:
                if getattr(self, 'fpv_ghost_actor', None) is None:
                    self.fpv_ghost_actor = vtk.vtkActor()
                    self.fpv_ghost_actor.SetMapper(self.ghost_actor.GetMapper())
                    self.fpv_ghost_actor.SetProperty(self.ghost_actor.GetProperty())
                    self.fpv_renderer.AddActor(self.fpv_ghost_actor)
                self.fpv_ghost_actor.SetVisibility(self.ghost_visible)
        
    def clear_ghost_trail(self):
        """Resets the breadcrumb trail."""
        if self.ghost_actor is not None:
            self.plotter.remove_actor(self.ghost_actor)
            self.ghost_actor = None
        if self.fpv_ghost_actor and self.fpv_renderer:
            self.fpv_renderer.RemoveActor(self.fpv_ghost_actor)
            self.fpv_ghost_actor = None
        self.plotter.update()

    def set_fpv_active(self, active):
        """Toggles the Picture-in-Picture FPV view."""
        self.fpv_active = active
        
        if active and self.fpv_renderer is None:
            # Create a raw VTK renderer for the inset
            import vtk
            self.fpv_renderer = vtk.vtkRenderer()
            self.fpv_renderer.SetViewport(0.02, 0.68, 0.32, 0.98)
            self.fpv_renderer.SetBackground(0.02, 0.02, 0.02) # Solid near-black
            
            # CRITICAL: Isolated viewport erasing
            # This makes the viewport opaque to the main renderer without using layers
            self.fpv_renderer.SetErase(1)
            self.fpv_renderer.SetInteractive(0) # Let clicks pass through to main view
            
            # Set the camera FOV
            self.fpv_renderer.GetActiveCamera().SetViewAngle(90.0)
            
            # Add it to the render window directly
            # Being added LAST ensures it is drawn ON TOP
            self.plotter.render_window.AddRenderer(self.fpv_renderer)
            
            # To see everything in FPV, we need to ensure the actors are in that renderer too
            self.sync_fpv_actors()
            
        if self.fpv_renderer:
            # Toggle visibility by setting viewport to 0 if inactive
            if active:
                self.fpv_renderer.SetViewport(0.02, 0.68, 0.32, 0.98)
            else:
                self.fpv_renderer.SetViewport(0, 0, 0, 0)
            
        self.plotter.update()

    def sync_fpv_actors(self):
        """Ensures all main actors are also present in the FPV renderer."""
        if not self.fpv_renderer:
            return
            
        import vtk
        # Clear existing FPV actors first to avoid duplicates
        self.fpv_renderer.RemoveAllViewProps()
        
        # 1. Map (Opaque for FPV)
        if self.map_actor:
            if not self.fpv_map_actor:
                self.fpv_map_actor = vtk.vtkActor()
                self.fpv_map_actor.SetMapper(self.map_actor.GetMapper())
            
            self.fpv_map_actor.SetTexture(self.map_actor.GetTexture())
            self.fpv_map_actor.GetProperty().DeepCopy(self.map_actor.GetProperty())
            self.fpv_map_actor.GetProperty().SetOpacity(1.0)
            self.fpv_map_actor.GetProperty().SetAmbient(0.8)
            self.fpv_map_actor.GetProperty().SetDiffuse(0.2)
            self.fpv_renderer.AddActor(self.fpv_map_actor)
            self.fpv_map_actor.SetVisibility(self.map_visible)

        # 2. Path
        if self.path_actor:
            if not self.fpv_path_actor:
                self.fpv_path_actor = vtk.vtkActor()
                self.fpv_path_actor.SetMapper(self.path_actor.GetMapper())
                self.fpv_path_actor.SetProperty(self.path_actor.GetProperty())
            self.fpv_renderer.AddActor(self.fpv_path_actor)

        # 3. Aircraft itself
        if self.aircraft_actor:
            self.fpv_renderer.AddActor(self.aircraft_actor)

        # 4. Ghost trail
        if self.ghost_actor:
            if not self.fpv_ghost_actor:
                self.fpv_ghost_actor = vtk.vtkActor()
                self.fpv_ghost_actor.SetMapper(self.ghost_actor.GetMapper())
                self.fpv_ghost_actor.SetProperty(self.ghost_actor.GetProperty())
            self.fpv_renderer.AddActor(self.fpv_ghost_actor)
            self.fpv_ghost_actor.SetVisibility(self.ghost_visible)
        
        # 5. Grid (CubeAxes) and Takeoff marker
        try:
            for actor in self.plotter.renderer.GetActors():
                # We want to catch the takeoff sphere marker if it exists
                if actor.GetMapper() and hasattr(actor, 'GetProperty'):
                    # Catch the takeoff marker (Red sphere)
                    color = actor.GetProperty().GetColor()
                    if color == (1.0, 0.0, 0.0): # Red
                        self.fpv_renderer.AddActor(actor)
                
                # Catch the Grid (vtkCubeAxesActor)
                if actor.GetClassName() == "vtkCubeAxesActor":
                    self.fpv_renderer.AddActor(actor)
        except:
            pass
            
        # 6. Re-add a stable border (LAST so it's on top)
        border_pts = vtk.vtkPoints()
        for p in [(0,0,0), (1,0,0), (1,1,0), (0,1,0)]: border_pts.InsertNextPoint(p)
        border_lines = vtk.vtkCellArray()
        border_lines.InsertNextCell(5)
        for i in [0,1,2,3,0]: border_lines.InsertCellPoint(i)
        border_poly = vtk.vtkPolyData()
        border_poly.SetPoints(border_pts)
        border_poly.SetLines(border_lines)
        border_mapper = vtk.vtkPolyDataMapper2D()
        border_mapper.SetInputData(border_poly)
        border_coord = vtk.vtkCoordinate()
        border_coord.SetCoordinateSystemToNormalizedViewport()
        border_mapper.SetTransformCoordinate(border_coord)
        self.fpv_border = vtk.vtkActor2D()
        self.fpv_border.SetMapper(border_mapper)
        self.fpv_border.GetProperty().SetColor(0.0, 0.66, 1.0)
        self.fpv_border.GetProperty().SetLineWidth(3)
        self.fpv_renderer.AddActor(self.fpv_border)

    def update_fpv_camera(self, pos, m):
        """Updates the FPV camera to look out from the nose of the aircraft."""
        if not self.fpv_renderer or not self.fpv_active:
            return
            
        # Nose position: the mesh tip is at X=3.25 at scale 5.0
        # We place the camera at 3.3 to be just outside the nose
        nose_offset = 3.3 
        
        # Extract forward (X) and up (Z) vectors from the aircraft matrix (4x4 numpy)
        # Column 0 is forward, Column 2 is up
        fwd = m[:3, 0]
        up = m[:3, 2]
        
        cam_pos = np.array(pos) + fwd * nose_offset
        focal_point = cam_pos + fwd * 100.0 # Look far ahead
        
        cam = self.fpv_renderer.GetActiveCamera()
        cam.SetPosition(tuple(cam_pos))
        cam.SetFocalPoint(tuple(focal_point))
        cam.SetViewUp(tuple(up))
        
        # Ensure clipping range is appropriate for the scale
        self.fpv_renderer.ResetCameraClippingRange()

    def follow_aircraft(self, pos):
        """
        Smoothly follows the aircraft while strictly preserving the user's current zoom and angle.
        """
        target_focal = np.array(pos, dtype=float)
        old_focal = np.array(self.plotter.camera.focal_point)
        old_pos = np.array(self.plotter.camera.position)
        
        # Calculate the current view vector (this IS the zoom and angle)
        view_vector = old_pos - old_focal
        
        # Determine tracking speed based on distance (closer = faster tracking)
        dist = np.linalg.norm(view_vector)
        base_t = 0.15 
        # Increase tracking tightness if we are zoomed in very close to prevent the plane escaping
        zoom_sensitivity = 50.0 / max(5.0, dist)
        t = min(1.0, base_t * max(1.0, zoom_sensitivity))
        
        # Move the focal point towards the aircraft
        new_focal = old_focal + t * (target_focal - old_focal)
        
        # Update camera position by maintaining the EXACT same view vector relative to the new focal point
        self.plotter.camera.focal_point = tuple(new_focal)
        self.plotter.camera.position = tuple(new_focal + view_vector)

    def render(self):
        """Single plotter update — call once per frame after all scene changes."""
        self.plotter.update()

    def set_ghost_visible(self, visible):
        """Sets the visibility of the breadcrumb trail."""
        self.ghost_visible = visible
        if self.ghost_actor is not None:
            self.ghost_actor.SetVisibility(visible)
        
        # If toggling ON, ensure the mesh is up to date
        if visible:
            self._update_ghost_mesh()
            
        self.plotter.update()
        if self.fpv_renderer:
            self.fpv_renderer.Render()

    def set_map_visible(self, visible):
        """Sets the visibility of the satellite map."""
        self.map_visible = visible
        if self.map_actor is not None:
            self.map_actor.SetVisibility(visible)
            self.plotter.update()
        if self.terrain_actor is not None:
            self.terrain_actor.SetVisibility(not visible)
            self.plotter.update()
        if self.fpv_map_actor is not None:
            self.fpv_map_actor.SetVisibility(visible)
            if self.fpv_renderer:
                self.fpv_renderer.Render()

    def set_map_opacity(self, opacity):
        """Sets the opacity of the satellite map (0.0 to 1.0)."""
        self.map_opacity = opacity
        if self.map_actor is not None:
            self.map_actor.GetProperty().SetOpacity(opacity)
            self.plotter.update()
