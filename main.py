import socket
import config
from signal_map import SignalMap
from xplane_udp import pack_rref_subscribe, pack_dref_set, parse_rref_response

def run():
    print("Loading signal map…")
    smap = SignalMap(config.SIGNAL_PNG, config.SIGNAL_KML)
    print(f"Signal map loaded. Bounds: N{smap.north} S{smap.south} E{smap.east} W{smap.west}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", config.LISTEN_PORT))
        sock.settimeout(1.0)

        xplane = (config.XPLANE_IP, config.XPLANE_PORT)
        sock.sendto(pack_rref_subscribe(config.IDX_LAT, config.DREF_LAT, config.RREF_FREQ), xplane)
        sock.sendto(pack_rref_subscribe(config.IDX_LON, config.DREF_LON, config.RREF_FREQ), xplane)
        print(f"Subscribed to position datarefs at {config.RREF_FREQ} Hz. Listening on port {config.LISTEN_PORT}…")

        lat = lon = None
        last_strength = None

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
                if strength != last_strength:
                    sock.sendto(pack_dref_set(config.DREF_SIGNAL, strength), xplane)
                    last_strength = strength
                print(f"lat={lat:.4f} lon={lon:.4f}  signal={strength:.4f}")
    finally:
        sock.close()

if __name__ == "__main__":
    run()
