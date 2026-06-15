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
