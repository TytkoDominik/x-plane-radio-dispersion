XPLANE_IP   = "127.0.0.1"
XPLANE_PORT = 49000      # X-Plane listens here for commands
LISTEN_PORT = 49001      # port this service listens on for RREF responses

RREF_FREQ   = 10         # position update rate in Hz

# Dataref indices (arbitrary integers used to match RREF responses)
IDX_LAT      = 0
IDX_LON      = 1
IDX_NAV1_OBS = 2

DREF_LAT    = "sim/flightmodel/position/latitude"
DREF_LON    = "sim/flightmodel/position/longitude"

# Nav needle override — must be 1.0 before writing nav1 needle datarefs
DREF_OVERRIDE_NAV   = "sim/operation/override/override_navneedles"

# Nav1 needle datarefs (writable only when override_navneedles=1)
DREF_NAV1_FROMTO    = "sim/cockpit/radios/nav1_fromto"            # 0=flag, 1=TO, 2=FROM
DREF_NAV1_FLAG_GS   = "sim/cockpit/radios/nav1_flag_glideslope"   # 1=flagged (no GS)
DREF_NAV1_HDEF      = "sim/cockpit/radios/nav1_hdef_dots"         # CDI deflection in dots

# OBS setting (read from X-Plane, used to compute FROM/TO)
DREF_NAV1_OBS       = "sim/cockpit/radios/nav1_obs_degm_pilot"    # degrees magnetic

# Signal strength below this → treat as no signal
SIGNAL_THRESHOLD = 0.15

VOR_LAT = 48.0226
VOR_LON = 12.8928

SIGNAL_PNG  = "VORSBG.png"
SIGNAL_KML  = "VORSBG.kml"
SIGNAL_MIN  = 0.01   # value sent for weakest signal (blue)
SIGNAL_MAX  = 1.0    # value sent for strongest signal (red)
