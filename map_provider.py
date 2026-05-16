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
        self.current_provider = "Satellite (ESRI)"
        self.custom_url = ""

    def set_provider(self, provider_name, custom_url=""):
        self.current_provider = provider_name
        if provider_name == "MapProxy / Custom":
            self.custom_url = custom_url

    def get_url_template(self):
        if self.current_provider == "MapProxy / Custom":
            return self.custom_url
        return self.providers.get(self.current_provider, self.providers["Satellite (ESRI)"])

    def get_max_zoom(self):
        """Return a provider-specific maximum usable XYZ tile zoom."""
        url_template = self.get_url_template().lower()
        # OpenTopoMap serves transparent overlay-like tiles above z17 in some
        # areas. In this viewer those can become a black texture, while z17 is
        # the normal rendered topographic map.
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

    def fetch_tile(self, x, y, z):
        url_template = self.get_url_template()
        if not url_template:
            return None
            
        # Use a provider-specific cache prefix to avoid mixing tiles
        provider_prefix = self.current_provider.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
        
        # If it's a custom URL, append a hash of the URL so changing URLs fetches new tiles
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
            # Use a more standard browser user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Referer': 'https://opentopomap.org/' if 'opentopomap' in url_template.lower() else ''
            }
            response = requests.get(url, timeout=10, headers=headers)
            if response.status_code == 200:
                # Handle images with transparency by pasting onto a white background
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
        """
        Fetches and stitches tiles to cover the bounding box.
        Returns (Image, bounds_latlon)
        bounds_latlon: (min_lat, max_lat, min_lon, max_lon) of the actual stitched image.
        """
        zoom = min(zoom, self.get_max_zoom())

        # Determine tile range
        x1, y1 = self.latlon_to_tile(max_lat, min_lon, zoom) # Top left
        x2, y2 = self.latlon_to_tile(min_lat, max_lon, zoom) # Bottom right
        
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
                
                # Abort early if the connection failed, rather than timing out 70+ times
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
        
        # Calculate actual bounds of the stitched image
        lat_top, lon_left = self.tile_to_latlon(x1, y1, zoom)
        lat_bottom, lon_right = self.tile_to_latlon(x2 + 1, y2 + 1, zoom)
        
        img_path = os.path.abspath("current_map.jpg")
        full_img.save(img_path)
        
        return img_path, (lat_bottom, lat_top, lon_left, lon_right)

    def get_elevation_grid(self, min_lat, max_lat, min_lon, max_lon, res=10):
        """
        Fetches elevation data for a grid of points.
        Returns a 2D numpy array of elevations.
        """
        lats = np.linspace(min_lat, max_lat, res)
        lons = np.linspace(min_lon, max_lon, res)
        
        locations = []
        for lat in reversed(lats): # Top to bottom
            for lon in lons:       # Left to right
                locations.append({"latitude": lat, "longitude": lon})
        
        print(f"Fetching elevation for {res}x{res} grid...")
        try:
            url = "https://api.open-elevation.com/api/v1/lookup"
            response = requests.post(url, json={"locations": locations}, timeout=10)
            if response.status_code == 200:
                results = response.json()["results"]
                elevations = np.array([r["elevation"] for r in results]).reshape(res, res)
                return elevations, lats, lons
        except Exception as e:
            print(f"Error fetching elevation: {e}")
        
        return None, None, None

if __name__ == "__main__":
    # Test with a known location (roughly the area in the log)
    provider = MapProvider()
    path, bounds = provider.get_map(51.784, 51.785, -2.408, -2.407)
    print(f"Map saved to {path}, bounds: {bounds}")
