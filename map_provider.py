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

import math
import requests
from PIL import Image
import io
import os
import numpy as np
import hashlib

class MapProvider:
    def __init__(self, cache_dir="map_cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        self.providers = {
            "Satellite (ESRI)": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "Street (OSM)": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "MapProxy / Custom": "" # User provided
        }
        self.terrain_providers = [
            "Mapzen Terrarium",
            "Open-Elevation",
            "OpenTopoData Mapzen",
            "OpenTopoData SRTM 30m",
            "OpenTopoData EU-DEM 25m",
        ]
        self.current_provider = "Satellite (ESRI)"
        self.current_terrain_provider = self.terrain_providers[0]
        self.custom_url = ""

    def set_provider(self, provider_name, custom_url=""):
        self.current_provider = provider_name
        if provider_name == "MapProxy / Custom":
            self.custom_url = custom_url

    def get_terrain_provider_names(self):
        return list(self.terrain_providers)

    def set_terrain_provider(self, provider_name):
        if provider_name == "Mapzen Terrarium (Preferred)":
            provider_name = "Mapzen Terrarium"
        if provider_name in self.terrain_providers:
            self.current_terrain_provider = provider_name
        else:
            self.current_terrain_provider = self.terrain_providers[0]

    def get_url_template(self):
        if self.current_provider == "MapProxy / Custom":
            return self.custom_url
        return self.providers.get(self.current_provider, self.providers["Satellite (ESRI)"])

    def get_max_zoom(self):
        """Return a provider-specific maximum usable XYZ tile zoom."""
        url_template = self.get_url_template().lower()
        if "opentopomap.org" in url_template:
            return 17
        return 18

    @staticmethod
    def _is_bad_cached_tile(img):
        """Detect stale all-black tiles created by older transparent PNG handling."""
        rgb = img.convert("RGB")
        extrema = rgb.getextrema()
        return all(channel_max <= 2 for _channel_min, channel_max in extrema)

    def latlon_to_tile(self, lat, lon, zoom):
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return xtile, ytile

    def tile_to_latlon(self, x, y, zoom):
        n = 2.0 ** zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg

    def latlon_to_tile_float(self, lat, lon, zoom):
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = (lon + 180.0) / 360.0 * n
        y = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
        return x, y

    def fetch_tile(self, x, y, z):
        url_template = self.get_url_template()
        if not url_template:
            return None
            
        provider_prefix = self.current_provider.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
        
        if self.current_provider == "MapProxy / Custom":
            url_hash = hashlib.md5(url_template.encode('utf-8')).hexdigest()[:8]
            provider_prefix = f"{provider_prefix}_{url_hash}"
            
        cache_path = os.path.join(self.cache_dir, f"{provider_prefix}_{z}_{x}_{y}.jpg")
        
        if os.path.exists(cache_path):
            try:
                cached = Image.open(cache_path).convert("RGB")
                if not self._is_bad_cached_tile(cached):
                    return cached
                os.remove(cache_path)
            except Exception:
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
            
        url = url_template.format(x=x, y=y, z=z)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Referer': 'https://opentopomap.org/' if 'opentopomap' in url_template.lower() else ''
            }
            response = requests.get(url, timeout=10, headers=headers)
            if response.status_code == 200:
                img_data = io.BytesIO(response.content)
                img = Image.open(img_data)
                
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    alpha = img.convert('RGBA').split()[-1]
                    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                    bg.paste(img, mask=alpha)
                    img = bg.convert('RGB')
                else:
                    img = img.convert('RGB')
                    
                img.save(cache_path, quality=85)
                return img
        except requests.exceptions.RequestException as e:
            if not getattr(self, '_connection_error_printed', False):
                print(f"Connection failed for map provider '{self.current_provider}'. Ensure URL is correct and server is running.")
                self._connection_error_printed = True
        except Exception as e:
            print(f"Error processing tile {x}, {y}, {z}: {e}")
        return None

    def get_map(self, min_lat, max_lat, min_lon, max_lon, zoom=18, progress_callback=None):
        zoom = min(zoom, self.get_max_zoom())
        x1, y1 = self.latlon_to_tile(max_lat, min_lon, zoom)
        x2, y2 = self.latlon_to_tile(min_lat, max_lon, zoom)
        
        tile_count_x = x2 - x1 + 1
        tile_count_y = y2 - y1 + 1
        total_tiles = tile_count_x * tile_count_y
        
        width = tile_count_x * 256
        height = tile_count_y * 256
        
        if width > 4000 or height > 4000:
            print("Area too large, reducing zoom...")
            return self.get_map(min_lat, max_lat, min_lon, max_lon, zoom - 1, progress_callback)
            
        self._connection_error_printed = False
        full_img = Image.new('RGB', (width, height), (255, 255, 255))
        
        pasted_count = 0
        tile_success_count = 0
        for i, x in enumerate(range(x1, x2 + 1)):
            for j, y in enumerate(range(y1, y2 + 1)):
                tile = self.fetch_tile(x, y, zoom)
                if getattr(self, '_connection_error_printed', False):
                    raise ConnectionError(f"Could not connect to map provider '{self.current_provider}'.")
                    
                if tile:
                    full_img.paste(tile, (i * 256, j * 256))
                    tile_success_count += 1
                
                pasted_count += 1
                if progress_callback:
                    progress_callback(pasted_count, total_tiles)

        if tile_success_count == 0:
            raise ConnectionError(f"No map tiles could be fetched from provider '{self.current_provider}'.")
        
        lat_top, lon_left = self.tile_to_latlon(x1, y1, zoom)
        lat_bottom, lon_right = self.tile_to_latlon(x2 + 1, y2 + 1, zoom)
        
        img_path = os.path.abspath("current_map.jpg")
        full_img.save(img_path)
        
        return img_path, (lat_bottom, lat_top, lon_left, lon_right)

    def get_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res=64, progress_callback=None):
        """
        Fetches elevation data for a grid of points.
        Returns a 2D numpy array of elevations (ASL in meters), ordered from
        north-to-south and west-to-east to match map tile image orientation.
        """
        source_key = self.current_terrain_provider.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_").lower()
        cache_key = hashlib.md5(f"{source_key}_{min_lat:.6f}_{max_lat:.6f}_{min_lon:.6f}_{max_lon:.6f}_{res}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"elevation_{cache_key}.npy")
        
        if os.path.exists(cache_path):
            try:
                elevations = np.load(cache_path)
                if elevations.ndim == 2:
                    if progress_callback:
                        progress_callback(1, 1)
                    return elevations
            except Exception:
                pass

        selected_provider = self.current_terrain_provider
        used_fallback = False
        if selected_provider == "OpenTopoData EU-DEM 25m":
            elevations = self._get_opentopodata_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, "eudem25m", progress_callback)
        elif selected_provider == "Open-Elevation":
            elevations = self._get_open_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, progress_callback)
        elif selected_provider == "Google Elevation":
            elevations = self._get_google_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, progress_callback)
        elif selected_provider == "OpenTopoData Mapzen":
            elevations = self._get_opentopodata_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, "mapzen", progress_callback)
        elif selected_provider == "OpenTopoData SRTM 30m":
            elevations = self._get_opentopodata_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, "srtm30m", progress_callback)
        elif selected_provider == "ESRI Terrain3D":
            elevations = self._get_esri_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, progress_callback)
        else:
            elevations = self._get_terrarium_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, progress_callback)

        if elevations is None and selected_provider != "Mapzen Terrarium":
            used_fallback = True
            elevations = self._get_terrarium_elevation_grid(min_lat, max_lat, min_lon, max_lon, res, progress_callback)

        if elevations is not None and not used_fallback:
            np.save(cache_path, elevations.astype(np.float32))
        return elevations

    def _get_esri_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res, progress_callback=None):
        url = "https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer/exportImage"
        params = {
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "bboxSR": 4326,
            "imageSR": 4326,
            "size": f"{res},{res}",
            "format": "tiff",
            "pixelType": "F32",
            "f": "image"
        }
        try:
            response = requests.get(url, params=params, timeout=15)
            if progress_callback:
                progress_callback(1, 1)
            if response.status_code != 200:
                return None
            img = Image.open(io.BytesIO(response.content))
            elevations = np.array(img).astype(np.float32)
            if elevations.ndim != 2:
                return None
            elevations[elevations < -10000] = np.nan
            if np.isnan(elevations).all():
                return None
            if np.isnan(elevations).any():
                elevations = np.nan_to_num(elevations, nan=float(np.nanmedian(elevations)))
            return elevations
        except Exception:
            return None

    def _terrain_zoom_for_bounds(self, min_lat, max_lat, min_lon, max_lon, max_tiles=16):
        for zoom in range(14, 8, -1):
            x1, y1 = self.latlon_to_tile(max_lat, min_lon, zoom)
            x2, y2 = self.latlon_to_tile(min_lat, max_lon, zoom)
            if (x2 - x1 + 1) * (y2 - y1 + 1) <= max_tiles:
                return zoom
        return 9

    def _fetch_terrarium_tile(self, x, y, z):
        cache_path = os.path.join(self.cache_dir, f"terrain_terrarium_{z}_{x}_{y}.png")
        try:
            if os.path.exists(cache_path):
                img = Image.open(cache_path).convert("RGB")
            else:
                url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    return None
                img = Image.open(io.BytesIO(response.content)).convert("RGB")
                img.save(cache_path)

            rgb = np.asarray(img, dtype=np.float32)
            return (rgb[:, :, 0] * 256.0 + rgb[:, :, 1] + rgb[:, :, 2] / 256.0) - 32768.0
        except Exception:
            return None

    @staticmethod
    def _sample_bilinear(grid, x, y):
        height, width = grid.shape
        x = float(np.clip(x, 0, width - 1))
        y = float(np.clip(y, 0, height - 1))
        x0 = int(np.floor(x))
        y0 = int(np.floor(y))
        x1 = min(x0 + 1, width - 1)
        y1 = min(y0 + 1, height - 1)
        dx = x - x0
        dy = y - y0

        q00 = grid[y0, x0]
        q10 = grid[y0, x1]
        q01 = grid[y1, x0]
        q11 = grid[y1, x1]
        if not np.isfinite([q00, q10, q01, q11]).all():
            vals = np.array([q00, q10, q01, q11], dtype=float)
            finite = vals[np.isfinite(vals)]
            return float(finite.mean()) if finite.size else np.nan

        return float(
            q00 * (1 - dx) * (1 - dy) +
            q10 * dx * (1 - dy) +
            q01 * (1 - dx) * dy +
            q11 * dx * dy
        )

    def _get_terrarium_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res, progress_callback=None):
        zoom = self._terrain_zoom_for_bounds(min_lat, max_lat, min_lon, max_lon)
        x1, y1 = self.latlon_to_tile(max_lat, min_lon, zoom)
        x2, y2 = self.latlon_to_tile(min_lat, max_lon, zoom)

        width = (x2 - x1 + 1) * 256
        height = (y2 - y1 + 1) * 256
        mosaic = np.full((height, width), np.nan, dtype=np.float32)

        fetched = 0
        checked = 0
        total_tiles = (x2 - x1 + 1) * (y2 - y1 + 1)
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                tile = self._fetch_terrarium_tile(x, y, zoom)
                if tile is not None:
                    px = (x - x1) * 256
                    py = (y - y1) * 256
                    mosaic[py:py + 256, px:px + 256] = tile
                    fetched += 1
                checked += 1
                if progress_callback:
                    progress_callback(checked, total_tiles)

        if fetched == 0 or np.isnan(mosaic).all():
            return None

        lats = np.linspace(max_lat, min_lat, res)
        lons = np.linspace(min_lon, max_lon, res)
        elevations = np.full((res, res), np.nan, dtype=np.float32)
        for row, lat in enumerate(lats):
            for col, lon in enumerate(lons):
                tile_x, tile_y = self.latlon_to_tile_float(lat, lon, zoom)
                px = (tile_x - x1) * 256.0
                py = (tile_y - y1) * 256.0
                elevations[row, col] = self._sample_bilinear(mosaic, px, py)

        if np.isnan(elevations).all():
            return None
        if np.isnan(elevations).any():
            elevations = np.nan_to_num(elevations, nan=float(np.nanmedian(elevations)))
        return elevations

    def _get_opentopodata_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res, dataset, progress_callback=None):
        lats = np.linspace(max_lat, min_lat, res)
        lons = np.linspace(min_lon, max_lon, res)
        points = [(lat, lon) for lat in lats for lon in lons]
        elevations = []
        total_batches = (len(points) + 99) // 100

        try:
            for batch_idx, start in enumerate(range(0, len(points), 100), start=1):
                chunk = points[start:start + 100]
                locations = "|".join(f"{lat:.7f},{lon:.7f}" for lat, lon in chunk)
                response = requests.get(
                    f"https://api.opentopodata.org/v1/{dataset}",
                    params={"locations": locations},
                    timeout=20
                )
                if response.status_code != 200:
                    return None
                data = response.json()
                if data.get("status") != "OK":
                    return None
                elevations.extend(
                    np.nan if item.get("elevation") is None else float(item["elevation"])
                    for item in data.get("results", [])
                )
                if progress_callback:
                    progress_callback(batch_idx, total_batches)
        except Exception as e:
            print(f"Error fetching OpenTopoData elevation: {e}")
            return None

        if len(elevations) != res * res:
            return None
        grid = np.array(elevations, dtype=np.float32).reshape(res, res)
        if np.isnan(grid).all():
            return None
        if np.isnan(grid).any():
            grid = np.nan_to_num(grid, nan=float(np.nanmedian(grid)))
        return grid

    def _get_open_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res, progress_callback=None):
        lats = np.linspace(max_lat, min_lat, res)
        lons = np.linspace(min_lon, max_lon, res)
        points = [{"latitude": float(lat), "longitude": float(lon)} for lat in lats for lon in lons]
        elevations = []
        total_batches = (len(points) + 99) // 100

        try:
            for batch_idx, start in enumerate(range(0, len(points), 100), start=1):
                response = requests.post(
                    "https://api.open-elevation.com/api/v1/lookup",
                    json={"locations": points[start:start + 100]},
                    timeout=20
                )
                if response.status_code != 200:
                    return None
                data = response.json()
                elevations.extend(
                    np.nan if item.get("elevation") is None else float(item["elevation"])
                    for item in data.get("results", [])
                )
                if progress_callback:
                    progress_callback(batch_idx, total_batches)
        except Exception:
            return None

        return self._elevation_list_to_grid(elevations, res)

    def _get_google_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res, progress_callback=None):
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_ELEVATION_API_KEY")
        if not api_key:
            return None

        lats = np.linspace(max_lat, min_lat, res)
        lons = np.linspace(min_lon, max_lon, res)
        points = [(lat, lon) for lat in lats for lon in lons]
        elevations = []
        total_batches = (len(points) + 511) // 512

        try:
            for batch_idx, start in enumerate(range(0, len(points), 512), start=1):
                chunk = points[start:start + 512]
                locations = "|".join(f"{lat:.7f},{lon:.7f}" for lat, lon in chunk)
                response = requests.get(
                    "https://maps.googleapis.com/maps/api/elevation/json",
                    params={"locations": locations, "key": api_key},
                    timeout=20
                )
                if response.status_code != 200:
                    return None
                data = response.json()
                if data.get("status") != "OK":
                    return None
                elevations.extend(
                    np.nan if item.get("elevation") is None else float(item["elevation"])
                    for item in data.get("results", [])
                )
                if progress_callback:
                    progress_callback(batch_idx, total_batches)
        except Exception:
            return None

        return self._elevation_list_to_grid(elevations, res)

    @staticmethod
    def _elevation_list_to_grid(elevations, res):
        if len(elevations) != res * res:
            return None
        grid = np.array(elevations, dtype=np.float32).reshape(res, res)
        if np.isnan(grid).all():
            return None
        if np.isnan(grid).any():
            grid = np.nan_to_num(grid, nan=float(np.nanmedian(grid)))
        return grid

if __name__ == "__main__":
    provider = MapProvider()
    path, bounds = provider.get_map(51.784, 51.785, -2.408, -2.407)
    print(f"Map saved to {path}, bounds: {bounds}")
