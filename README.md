# X-Plane Radio Signal Service

Feeds X-Plane 11 with real-time VOR radio signal strength based on pre-calculated propagation data (VORSBG, 144 MHz). Reads plane position via UDP and writes signal strength back to the simulator.

## Requirements

- Windows 10/11
- X-Plane 11
- Python 3.10 or newer — [python.org/downloads](https://www.python.org/downloads/) *(check "Add Python to PATH" during install)*
- `VORSBG.png` and `VORSBG.kml` signal map files in the project folder

## Setup

### 1. Configure X-Plane networking

In X-Plane: **Settings → Network**

- Enable **"Send network data output"** to IP `127.0.0.1`, port `49001`

### 2. Install dependencies

Double-click `setup.bat` — installs `numpy`, `Pillow`, and `pytest`.

Or run manually:
```
pip install -r requirements.txt
```

## Running

Double-click `run.bat`, or from the project folder:

```
python main.py
```

X-Plane must be running before or shortly after starting the service.

### Expected output

```
Loading signal map…
Signal map loaded. Bounds: N49.80238 S46.20283 E15.58265 W10.20295
Subscribed to position datarefs at 10 Hz. Listening on port 49001…
lat=48.0100 lon=12.9200  signal=0.9800
lat=48.0102 lon=12.9201  signal=0.9800
```

- **No output after "Listening…"** — X-Plane network output not configured, or wrong port
- **Output stops** — plane flew outside VORSBG coverage area; no signal sent to X-Plane

Stop with `Ctrl+C`.

## Configuration

Edit `config.py` to change defaults:

| Setting | Default | Description |
|---|---|---|
| `XPLANE_IP` | `127.0.0.1` | X-Plane machine IP |
| `XPLANE_PORT` | `49000` | Port X-Plane listens on |
| `LISTEN_PORT` | `49001` | Port this service listens on |
| `RREF_FREQ` | `10` | Position update rate (Hz) |
| `DREF_SIGNAL` | `sim/cockpit/radios/nav1_signal_quality_test` | Dataref written with signal strength |

## Coverage area

VORSBG VOR station — Austria/Czech Republic region:

- North: 49.80°, South: 46.20°, West: 10.20°, East: 15.58°

Signal strength scale: `1.0` = maximum (red), `0.01` = minimum (blue), no transmission outside bounds.

## Running tests

```
python -m pytest tests/ -v
```
