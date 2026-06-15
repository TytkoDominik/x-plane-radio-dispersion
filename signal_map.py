from __future__ import annotations
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

class SignalMap:
    def __init__(self, png_path: str, kml_path: str, signal_min: float = 0.01, signal_max: float = 1.0):
        self.north, self.south, self.east, self.west = self._parse_kml(kml_path)
        self._grid = self._load_png(png_path, signal_min, signal_max)   # 2D float32 array [h, w]
        self._h, self._w = self._grid.shape

    def _parse_kml(self, path: str):
        ns  = {"k": "http://www.opengis.net/kml/2.2"}
        tree = ET.parse(path)
        root = tree.getroot()
        box  = root.find(".//k:LatLonBox", ns)
        if box is None:
            box = root.find(".//LatLonBox")
        def f(tag):
            el = box.find(f"k:{tag}", ns)
            if el is None:
                el = box.find(tag)
            return float(el.text.strip())
        return f("north"), f("south"), f("east"), f("west")

    def _load_png(self, path: str, signal_min: float, signal_max: float) -> np.ndarray:
        img  = Image.open(path).convert("RGBA")
        arr  = np.array(img, dtype=np.float32)  # [h, w, 4]
        r, g, b, a = arr[...,0], arr[...,1], arr[...,2], arr[...,3]

        cmax  = np.maximum(np.maximum(r, g), b)
        cmin  = np.minimum(np.minimum(r, g), b)
        delta = cmax - cmin

        hue = np.zeros((arr.shape[0], arr.shape[1]), dtype=np.float32)
        m = delta > 0
        gr = m & (cmax == r)
        hue[gr] = (60 * ((g[gr] - b[gr]) / delta[gr])) % 360
        gg = m & (cmax == g)
        hue[gg] = 60 * ((b[gg] - r[gg]) / delta[gg] + 2)
        gb = m & (cmax == b)
        hue[gb] = 60 * ((r[gb] - g[gb]) / delta[gb] + 4)

        # hue 0(red)→signal_max, hue 240(blue)→signal_min, transparent→0.0
        strength = np.where(a > 10,
                            np.clip(signal_min + (signal_max - signal_min) * (1.0 - hue / 240.0),
                                    signal_min, signal_max),
                            0.0)
        return strength.astype(np.float32)

    def lookup(self, lon: float, lat: float) -> float | None:
        if not (self.west <= lon <= self.east and self.south <= lat <= self.north):
            return None
        x = round((lon - self.west)  / (self.east  - self.west)  * (self._w - 1))
        y = round((self.north - lat) / (self.north - self.south) * (self._h - 1))
        x = max(0, min(x, self._w - 1))
        y = max(0, min(y, self._h - 1))
        return float(self._grid[y, x])
