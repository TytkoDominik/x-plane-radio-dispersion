# X-Plane Radio Signal Strength Service — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python service that continuously feeds X-Plane 11 with radio signal strength for VORSBG (144 MHz) based on pre-calculated propagation data and the plane's current lon/lat position.

**Architecture:** A UDP loop subscribes to X-Plane position datarefs via `RREF`, receives lat/lon updates, performs O(1) pixel-coordinate lookup against the VORSBG.png signal map, and writes the result back to X-Plane via `DREF`. The signal map is loaded once at startup as a numpy float32 array derived directly from the PNG — no CSV involved.

**Tech Stack:** Python 3.12, `numpy`, `Pillow`, `pytest`, Python stdlib `socket` / `struct` / `xml.etree.ElementTree`

---

## File Structure

```
x-plane-integration/
├── config.py             - X-Plane IP/ports, RREF indices, dataref names, signal map path
├── signal_map.py         - loads VORSBG.png + KML bounds → O(1) (lon,lat)→strength lookup
├── xplane_udp.py         - UDP packet helpers: subscribe_rref, parse_rref_response, send_dref
├── main.py               - main loop: subscribe → receive → lookup → send
└── tests/
    ├── test_signal_map.py
    └── test_xplane_udp.py
```

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`

- [ ] **Step 1: Install dependencies**

```bash
pip3 install --break-system-packages numpy Pillow pytest
```

Expected output: `Successfully installed ...` (or `already satisfied`)

- [ ] **Step 2: Create requirements.txt**

```
numpy>=1.26
Pillow>=10.0
pytest>=8.0
```

- [ ] **Step 3: Create tests package**

```bash
mkdir -p tests && touch tests/__init__.py
```

- [ ] **Step 4: Verify pytest works**

```bash
python3 -m pytest tests/ -v
```

Expected: `no tests ran` — no errors.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/__init__.py
git commit -m "chore: project setup for X-Plane radio signal service"
```

---

### Task 2: Config

**Files:**
- Create: `config.py`

- [ ] **Step 1: Write config.py**

```python
XPLANE_IP   = "127.0.0.1"
XPLANE_PORT = 49000      # X-Plane listens here for commands
LISTEN_PORT = 49001      # port this service listens on for RREF responses

RREF_FREQ   = 10         # position update rate in Hz

# Dataref indices (arbitrary integers used to match RREF responses)
IDX_LAT = 0
IDX_LON = 1

DREF_LAT    = "sim/flightmodel/position/latitude"
DREF_LON    = "sim/flightmodel/position/longitude"
DREF_SIGNAL = "sim/cockpit/radios/nav1_signal_quality_test"

SIGNAL_PNG  = "VORSBG.png"
SIGNAL_KML  = "VORSBG.kml"
```

- [ ] **Step 2: Commit**

```bash
git add config.py
git commit -m "chore: add config for X-Plane UDP and signal map paths"
```

---

### Task 3: Signal Map (TDD)

**Files:**
- Create: `tests/test_signal_map.py`
- Create: `signal_map.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_signal_map.py
import pytest
from signal_map import SignalMap

KML  = "VORSBG.kml"
PNG  = "VORSBG.png"

@pytest.fixture(scope="module")
def smap():
    return SignalMap(PNG, KML)

def test_loads_bounds(smap):
    assert abs(smap.north - 49.80238) < 0.001
    assert abs(smap.south - 46.20283) < 0.001
    assert abs(smap.east  - 15.58265) < 0.001
    assert abs(smap.west  - 10.20295) < 0.001

def test_in_bounds_returns_float(smap):
    # Centre of coverage area — VORSBG transmitter site
    strength = smap.lookup(lon=12.8928, lat=48.0026)
    assert isinstance(strength, float)
    assert 0.0 <= strength <= 1.0

def test_outside_bounds_returns_zero(smap):
    assert smap.lookup(lon=0.0, lat=0.0) == 0.0

def test_transparent_pixel_returns_zero(smap):
    # Top-left corner of PNG is outside coverage — transparent
    strength = smap.lookup(lon=smap.west, lat=smap.north)
    assert strength == 0.0

def test_strong_signal_near_transmitter(smap):
    # Red pixels (strength≈1.0) should be near the transmitter
    strength = smap.lookup(lon=12.8928, lat=48.0026)
    assert strength > 0.5
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python3 -m pytest tests/test_signal_map.py -v
```

Expected: `ModuleNotFoundError: No module named 'signal_map'`

- [ ] **Step 3: Write signal_map.py**

```python
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

class SignalMap:
    def __init__(self, png_path: str, kml_path: str):
        self.north, self.south, self.east, self.west = self._parse_kml(kml_path)
        self._grid = self._load_png(png_path)   # 2D float32 array [h, w]
        self._h, self._w = self._grid.shape

    def _parse_kml(self, path: str):
        ns  = {"k": "http://www.opengis.net/kml/2.2"}
        tree = ET.parse(path)
        root = tree.getroot()
        box  = root.find(".//k:LatLonBox", ns)
        if box is None:
            # try without namespace
            box = root.find(".//LatLonBox")
        def f(tag):
            el = box.find(f"k:{tag}", ns) or box.find(tag)
            return float(el.text.strip())
        return f("north"), f("south"), f("east"), f("west")

    def _load_png(self, path: str) -> np.ndarray:
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

        # hue 0(red)→1.0, hue 240(blue)→0.01, transparent→0.0
        strength = np.where(a > 10,
                            np.clip(0.01 + 0.99 * (1.0 - hue / 240.0), 0.01, 1.0),
                            0.0)
        return strength.astype(np.float32)

    def lookup(self, lon: float, lat: float) -> float:
        if not (self.west <= lon <= self.east and self.south <= lat <= self.north):
            return 0.0
        x = round((lon - self.west)  / (self.east  - self.west)  * (self._w - 1))
        y = round((self.north - lat) / (self.north - self.south) * (self._h - 1))
        x = max(0, min(x, self._w - 1))
        y = max(0, min(y, self._h - 1))
        return float(self._grid[y, x])
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python3 -m pytest tests/test_signal_map.py -v
```

Expected: 5 PASSED (loading the 8000×8000 PNG takes ~5 s on first run).

- [ ] **Step 5: Commit**

```bash
git add signal_map.py tests/test_signal_map.py
git commit -m "feat: signal map with O(1) lon/lat lookup from VORSBG PNG"
```

---

### Task 4: X-Plane UDP Helpers (TDD)

**Files:**
- Create: `tests/test_xplane_udp.py`
- Create: `xplane_udp.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_xplane_udp.py
import struct
import pytest
from xplane_udp import pack_rref_subscribe, pack_dref_set, parse_rref_response

def test_pack_rref_subscribe_header():
    pkt = pack_rref_subscribe(index=0, dataref="sim/flightmodel/position/latitude", freq=10)
    assert pkt[:5] == b"RREF\x00"

def test_pack_rref_subscribe_length():
    pkt = pack_rref_subscribe(index=0, dataref="sim/flightmodel/position/latitude", freq=10)
    assert len(pkt) == 413  # 5 + 4 + 4 + 400

def test_pack_rref_subscribe_values():
    pkt = pack_rref_subscribe(index=7, dataref="sim/test", freq=5)
    _, freq, idx = struct.unpack_from("<xii", pkt[::-1][::-1], 5)  # skip header
    # re-unpack cleanly
    freq2, idx2 = struct.unpack_from("<ii", pkt, 5)
    assert freq2 == 5
    assert idx2 == 7

def test_pack_dref_set_header():
    pkt = pack_dref_set(dataref="sim/cockpit/radios/nav1_signal_quality_test", value=0.75)
    assert pkt[:5] == b"DREF\x00"

def test_pack_dref_set_length():
    pkt = pack_dref_set(dataref="sim/cockpit/radios/nav1_signal_quality_test", value=0.75)
    assert len(pkt) == 509  # 5 + 4 + 500

def test_pack_dref_set_value():
    pkt = pack_dref_set(dataref="sim/cockpit/radios/nav1_signal_quality_test", value=0.75)
    (val,) = struct.unpack_from("<f", pkt, 5)
    assert abs(val - 0.75) < 1e-5

def test_parse_rref_response_single():
    # Build a fake RREF response: header + one (index=0, value=48.0026)
    body = struct.pack("<if", 0, 48.0026)
    pkt  = b"RREF\x00" + body
    result = parse_rref_response(pkt)
    assert len(result) == 1
    assert result[0][0] == 0
    assert abs(result[0][1] - 48.0026) < 1e-3

def test_parse_rref_response_multiple():
    body = struct.pack("<if", 0, 48.0026) + struct.pack("<if", 1, 12.8928)
    pkt  = b"RREF\x00" + body
    result = parse_rref_response(pkt)
    assert len(result) == 2
    assert result[1][0] == 1
    assert abs(result[1][1] - 12.8928) < 1e-3

def test_parse_rref_ignores_wrong_header():
    pkt = b"XXXX\x00" + struct.pack("<if", 0, 1.0)
    assert parse_rref_response(pkt) == []
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python3 -m pytest tests/test_xplane_udp.py -v
```

Expected: `ModuleNotFoundError: No module named 'xplane_udp'`

- [ ] **Step 3: Write xplane_udp.py**

```python
import struct
from typing import List, Tuple

def pack_rref_subscribe(index: int, dataref: str, freq: int = 10) -> bytes:
    dref_bytes = dataref.encode().ljust(400, b"\x00")[:400]
    return struct.pack("<4sxii400s", b"RREF", freq, index, dref_bytes)

def pack_dref_set(dataref: str, value: float) -> bytes:
    dref_bytes = dataref.encode().ljust(500, b"\x00")[:500]
    return struct.pack("<4sxf500s", b"DREF", value, dref_bytes)

def parse_rref_response(data: bytes) -> List[Tuple[int, float]]:
    if len(data) < 5 or data[:4] != b"RREF":
        return []
    results = []
    offset = 5
    while offset + 8 <= len(data):
        index, value = struct.unpack_from("<if", data, offset)
        results.append((index, value))
        offset += 8
    return results
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python3 -m pytest tests/test_xplane_udp.py -v
```

Expected: 9 PASSED

- [ ] **Step 5: Commit**

```bash
git add xplane_udp.py tests/test_xplane_udp.py
git commit -m "feat: X-Plane UDP packet helpers for RREF and DREF"
```

---

### Task 5: Main Loop

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write main.py**

```python
import socket
import time
import config
from signal_map import SignalMap
from xplane_udp import pack_rref_subscribe, pack_dref_set, parse_rref_response

def run():
    print("Loading signal map…")
    smap = SignalMap(config.SIGNAL_PNG, config.SIGNAL_KML)
    print(f"Signal map loaded. Bounds: N{smap.north} S{smap.south} E{smap.east} W{smap.west}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", config.LISTEN_PORT))
    sock.settimeout(1.0)

    xplane = (config.XPLANE_IP, config.XPLANE_PORT)

    # Subscribe to lat and lon datarefs
    sock.sendto(pack_rref_subscribe(config.IDX_LAT, config.DREF_LAT, config.RREF_FREQ), xplane)
    sock.sendto(pack_rref_subscribe(config.IDX_LON, config.DREF_LON, config.RREF_FREQ), xplane)
    print(f"Subscribed to position datarefs at {config.RREF_FREQ} Hz. Listening on port {config.LISTEN_PORT}…")

    lat = lon = None

    while True:
        try:
            data, _ = sock.recvfrom(4096)
        except socket.timeout:
            continue

        for index, value in parse_rref_response(data):
            if index == config.IDX_LAT:
                lat = value
            elif index == config.IDX_LON:
                lon = value

        if lat is not None and lon is not None:
            strength = smap.lookup(lon=lon, lat=lat)
            sock.sendto(pack_dref_set(config.DREF_SIGNAL, strength), xplane)
            print(f"lat={lat:.4f} lon={lon:.4f}  signal={strength:.4f}")

if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run all tests — verify nothing broken**

```bash
python3 -m pytest tests/ -v
```

Expected: 14 PASSED

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main loop — subscribes to X-Plane position, feeds signal strength via DREF"
```

---

### Task 6: Manual Integration Test

> No X-Plane running? Use netcat to simulate packets.

- [ ] **Step 1: Start the service**

```bash
python3 main.py
```

Expected output:
```
Loading signal map…
Signal map loaded. Bounds: N49.80238 S46.20283 E15.58265 W10.20295
Subscribed to position datarefs at 10 Hz. Listening on port 49001…
```

- [ ] **Step 2: Simulate an RREF position response (separate terminal)**

```bash
python3 - <<'EOF'
import socket, struct

# Fake RREF response: lat=48.0026 (idx=0), lon=12.8928 (idx=1)
body = struct.pack("<if", 0, 48.0026) + struct.pack("<if", 1, 12.8928)
pkt  = b"RREF\x00" + body

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(pkt, ("127.0.0.1", 49001))
sock.close()
print("Sent fake position: lat=48.0026 lon=12.8928")
EOF
```

- [ ] **Step 3: Verify output in service terminal**

Expected:
```
lat=48.0026 lon=12.8928  signal=<value between 0.01 and 1.0>
```

Signal should be > 0.5 — this is near the VORSBG transmitter (strong coverage).

- [ ] **Step 4: Test outside-bounds position**

```bash
python3 - <<'EOF'
import socket, struct
body = struct.pack("<if", 0, 10.0) + struct.pack("<if", 1, 0.0)
pkt  = b"RREF\x00" + body
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(pkt, ("127.0.0.1", 49001))
sock.close()
print("Sent fake position: lat=10.0 lon=0.0 (outside coverage)")
EOF
```

Expected service output:
```
lat=10.0000 lon=0.0000  signal=0.0000
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "docs: integration test instructions in plan"
```

---

## X-Plane 11 Configuration Notes

**Net settings (X-Plane → Settings → Network):**
- IP of data receiver: `127.0.0.1` (same machine) or service machine IP
- Port to send RREF data: `49001` (must match `LISTEN_PORT` in config.py)
- This service sends commands to X-Plane on port `49000` (X-Plane default)

**Dataref writability:** `sim/cockpit/radios/nav1_signal_quality_test` requires X-Plane to be in developer mode (`--developer` flag) or a plugin like [FlyWithLua](https://forums.x-plane.org/index.php?/files/file/38445-flywithlua-ng-next-generation-edition-for-x-plane-11-win-lin-mac/) to expose it as writable. If the signal DREF write is silently ignored, switch to a custom FlyWithLua script that reads a UDP value and applies it.
