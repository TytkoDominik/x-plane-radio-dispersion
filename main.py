import math
import socket
import config
from signal_map import SignalMap
from xplane_udp import pack_rref_subscribe, pack_dref_set, parse_rref_response

def send_dref(sock, xplane, dataref: str, value: float) -> None:
    sock.sendto(pack_dref_set(dataref, value), xplane)


def compute_fromto(ac_lat: float, ac_lon: float, vor_lat: float, vor_lon: float, obs_deg: float) -> int:
    """Compute VOR FROM/TO flag geometrically. Returns 1=TO, 2=FROM."""
    d_lon = math.radians(vor_lon - ac_lon)
    lat1  = math.radians(ac_lat)
    lat2  = math.radians(vor_lat)
    x = math.sin(d_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    bearing = math.degrees(math.atan2(x, y)) % 360
    diff = ((bearing - obs_deg + 180) % 360) - 180
    return 1 if abs(diff) <= 90 else 2


def apply_nav1_state(sock, xplane, strength, fromto: int) -> str:
    """Drive Nav1 needle based on signal strength. Override held inside map bounds."""
    if strength is None:
        send_dref(sock, xplane, config.DREF_OVERRIDE_NAV, 0.0)
        return "OUT OF BOUNDS"
    send_dref(sock, xplane, config.DREF_OVERRIDE_NAV, 1.0)
    if strength < config.SIGNAL_THRESHOLD:
        send_dref(sock, xplane, config.DREF_NAV1_FROMTO, 0.0)
        send_dref(sock, xplane, config.DREF_NAV1_FLAG_GS, 1.0)
        send_dref(sock, xplane, config.DREF_NAV1_HDEF, 0.0)
        return "NO SIGNAL"
    else:
        send_dref(sock, xplane, config.DREF_NAV1_FROMTO, float(fromto))
        send_dref(sock, xplane, config.DREF_NAV1_FLAG_GS, 0.0)
        send_dref(sock, xplane, config.DREF_NAV1_HDEF, 0.0)
        return f"signal={strength:.4f} nav1_fromto={fromto}"


def run():
    print("Loading signal map…")
    smap = SignalMap(config.SIGNAL_PNG, config.SIGNAL_KML, config.SIGNAL_MIN, config.SIGNAL_MAX)
    vor_lat, vor_lon = config.VOR_LAT, config.VOR_LON
    print(f"Signal map loaded. Bounds: N{smap.north} S{smap.south} E{smap.east} W{smap.west}")
    print(f"VOR: lat={vor_lat} lon={vor_lon}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", config.LISTEN_PORT))
        sock.settimeout(1.0)

        xplane = (config.XPLANE_IP, config.XPLANE_PORT)

        sock.sendto(pack_rref_subscribe(config.IDX_LAT, config.DREF_LAT, config.RREF_FREQ), xplane)
        sock.sendto(pack_rref_subscribe(config.IDX_LON, config.DREF_LON, config.RREF_FREQ), xplane)
        sock.sendto(pack_rref_subscribe(config.IDX_NAV1_OBS, config.DREF_NAV1_OBS, config.RREF_FREQ), xplane)
        print(f"Subscribed to position + nav1_obs datarefs at {config.RREF_FREQ} Hz. Listening on port {config.LISTEN_PORT}…")

        lat = lon = None
        obs_deg = 0.0
        last_strength = None
        last_fromto = None

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
                elif index == config.IDX_NAV1_OBS:
                    obs_deg = value

            if lat is not None and lon is not None:
                strength = smap.lookup(lon=lon, lat=lat)
                fromto = compute_fromto(lat, lon, vor_lat, vor_lon, obs_deg) if strength else 0
                if strength != last_strength or fromto != last_fromto:
                    label = apply_nav1_state(sock, xplane, strength, fromto)
                    last_strength = strength
                    last_fromto = fromto
                    print(f"lat={lat:.4f} lon={lon:.4f}  {label}")
    finally:
        send_dref(sock, xplane, config.DREF_OVERRIDE_NAV, 0.0)
        sock.close()

if __name__ == "__main__":
    run()
