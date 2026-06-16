import socket
import config
from signal_map import SignalMap
from xplane_udp import pack_rref_subscribe, pack_dref_set, parse_rref_response

def send_dref(sock, xplane, dataref: str, value: float) -> None:
    sock.sendto(pack_dref_set(dataref, value), xplane)


def apply_nav1_state(sock, xplane, strength, nav1_fromto_raw) -> str:
    """Drive Nav1 needle based on signal strength. Override held inside map bounds."""
    if strength is None:
        # Outside map — release control entirely
        send_dref(sock, xplane, config.DREF_OVERRIDE_NAV, 0.0)
        return "OUT OF BOUNDS"
    # Inside map — keep override so X-Plane can't overwrite our values
    send_dref(sock, xplane, config.DREF_OVERRIDE_NAV, 1.0)
    if strength < config.SIGNAL_THRESHOLD:
        send_dref(sock, xplane, config.DREF_NAV1_FROMTO, 0.0)    # flagged
        send_dref(sock, xplane, config.DREF_NAV1_FLAG_GS, 1.0)   # GS flagged
        send_dref(sock, xplane, config.DREF_NAV1_HDEF, 0.0)
        return "NO SIGNAL"
    else:
        send_dref(sock, xplane, config.DREF_NAV1_FROMTO, nav1_fromto_raw)
        send_dref(sock, xplane, config.DREF_NAV1_FLAG_GS, 0.0)   # GS valid
        send_dref(sock, xplane, config.DREF_NAV1_HDEF, 0.0)
        return f"signal={strength:.4f} nav1_fromto={int(nav1_fromto_raw)}"


def run():
    print("Loading signal map…")
    smap = SignalMap(config.SIGNAL_PNG, config.SIGNAL_KML, config.SIGNAL_MIN, config.SIGNAL_MAX)
    print(f"Signal map loaded. Bounds: N{smap.north} S{smap.south} E{smap.east} W{smap.west}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", config.LISTEN_PORT))
        sock.settimeout(1.0)

        xplane = (config.XPLANE_IP, config.XPLANE_PORT)

        sock.sendto(pack_rref_subscribe(config.IDX_LAT, config.DREF_LAT, config.RREF_FREQ), xplane)
        sock.sendto(pack_rref_subscribe(config.IDX_LON, config.DREF_LON, config.RREF_FREQ), xplane)
        sock.sendto(pack_rref_subscribe(config.IDX_NAV1_FROMTO, config.DREF_NAV1_FROMTO, config.RREF_FREQ), xplane)
        print(f"Subscribed to position + nav1_fromto datarefs at {config.RREF_FREQ} Hz. Listening on port {config.LISTEN_PORT}…")

        lat = lon = None
        nav1_fromto_raw = 0.0
        last_strength = None
        last_nav1_fromto_raw = None

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
                elif index == config.IDX_NAV1_FROMTO:
                    nav1_fromto_raw = value

            if lat is not None and lon is not None:
                strength = smap.lookup(lon=lon, lat=lat)
                if strength != last_strength or nav1_fromto_raw != last_nav1_fromto_raw:
                    label = apply_nav1_state(sock, xplane, strength, nav1_fromto_raw)
                    last_strength = strength
                    last_nav1_fromto_raw = nav1_fromto_raw
                    print(f"lat={lat:.4f} lon={lon:.4f}  {label}")
    finally:
        # Release nav override on exit
        send_dref(sock, xplane, config.DREF_OVERRIDE_NAV, 0.0)
        sock.close()

if __name__ == "__main__":
    run()
