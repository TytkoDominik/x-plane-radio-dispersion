import struct
import pytest
from unittest.mock import MagicMock, call

import config
from xplane_udp import pack_dref_set
from main import apply_nav1_state

XPLANE = (config.XPLANE_IP, config.XPLANE_PORT)

STRONG = 0.5   # well above SIGNAL_THRESHOLD (0.15)
WEAK   = 0.10  # well below SIGNAL_THRESHOLD (0.15)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sent_packets(sock):
    """Return the list of (dataref, value) pairs decoded from all sendto calls."""
    results = []
    for c in sock.sendto.call_args_list:
        packet = c.args[0]
        # Packet layout: 5-byte header (b"DREF\x00"), 4-byte float, 500-byte dataref
        (value,) = struct.unpack_from("<f", packet, 5)
        dataref_raw = packet[9:509]
        dataref = dataref_raw.rstrip(b"\x00").decode()
        results.append((dataref, value))
    return results


def sent_value_for(sock, dataref):
    """Return the float value last sent for a specific dataref, or raise if not sent."""
    matches = [(dr, val) for dr, val in sent_packets(sock) if dr == dataref]
    if not matches:
        raise KeyError(f"dataref {dataref!r} was never sent")
    return matches[-1][1]


def was_sent(sock, dataref):
    return any(dr == dataref for dr, _ in sent_packets(sock))


# ---------------------------------------------------------------------------
# nav1_fromto pass-through under strong signal
# ---------------------------------------------------------------------------

def test_strong_signal_fromto_raw_1_sends_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, nav1_fromto_raw=1.0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 1.0) < 1e-5, f"expected nav1_fromto=1.0, got {val}"


def test_strong_signal_fromto_raw_2_sends_2():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, nav1_fromto_raw=2.0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 2.0) < 1e-5, f"expected nav1_fromto=2.0, got {val}"


def test_strong_signal_fromto_raw_0_sends_0():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, nav1_fromto_raw=0.0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, f"expected nav1_fromto=0.0, got {val}"


# ---------------------------------------------------------------------------
# Weak signal forces nav1_fromto=0.0 regardless of raw value
# ---------------------------------------------------------------------------

def test_weak_signal_fromto_overridden_to_0_when_raw_is_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, nav1_fromto_raw=1.0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, (
        f"weak signal should force nav1_fromto=0.0, got {val}"
    )


def test_weak_signal_fromto_overridden_to_0_when_raw_is_2():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, nav1_fromto_raw=2.0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, (
        f"weak signal should force nav1_fromto=0.0, got {val}"
    )


# ---------------------------------------------------------------------------
# Out of bounds (strength=None)
# ---------------------------------------------------------------------------

def test_out_of_bounds_sends_override_0():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=None, nav1_fromto_raw=1.0)
    val = sent_value_for(sock, config.DREF_OVERRIDE_NAV)
    assert abs(val - 0.0) < 1e-5, (
        f"out-of-bounds should release override (0.0), got {val}"
    )


def test_out_of_bounds_does_not_send_nav1_fromto():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=None, nav1_fromto_raw=1.0)
    assert not was_sent(sock, config.DREF_NAV1_FROMTO), (
        "out-of-bounds must not write nav1_fromto"
    )


# ---------------------------------------------------------------------------
# Override and flag_gs under strong vs weak signal
# ---------------------------------------------------------------------------

def test_strong_signal_sends_override_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, nav1_fromto_raw=1.0)
    val = sent_value_for(sock, config.DREF_OVERRIDE_NAV)
    assert abs(val - 1.0) < 1e-5, (
        f"strong signal should hold override at 1.0, got {val}"
    )


def test_strong_signal_sends_flag_gs_0():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, nav1_fromto_raw=1.0)
    val = sent_value_for(sock, config.DREF_NAV1_FLAG_GS)
    assert abs(val - 0.0) < 1e-5, (
        f"strong signal should clear GS flag (0.0), got {val}"
    )


def test_weak_signal_sends_override_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, nav1_fromto_raw=0.0)
    val = sent_value_for(sock, config.DREF_OVERRIDE_NAV)
    assert abs(val - 1.0) < 1e-5, (
        f"weak (but in-bounds) signal should keep override at 1.0, got {val}"
    )


def test_weak_signal_sends_flag_gs_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, nav1_fromto_raw=0.0)
    val = sent_value_for(sock, config.DREF_NAV1_FLAG_GS)
    assert abs(val - 1.0) < 1e-5, (
        f"weak signal should raise GS flag (1.0), got {val}"
    )


# ---------------------------------------------------------------------------
# Packet bytes match what pack_dref_set produces (end-to-end encoding check)
# ---------------------------------------------------------------------------

def test_strong_signal_packet_bytes_match_pack_dref_set():
    """Bytes sent to the socket must exactly equal pack_dref_set output."""
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, nav1_fromto_raw=1.0)
    # Find the call that sent nav1_fromto
    expected = pack_dref_set(config.DREF_NAV1_FROMTO, 1.0)
    actual_packets = [c.args[0] for c in sock.sendto.call_args_list]
    assert expected in actual_packets, (
        "the raw bytes for nav1_fromto=1.0 were not found among the sent packets"
    )


# ---------------------------------------------------------------------------
# Return-value strings
# ---------------------------------------------------------------------------

def test_out_of_bounds_returns_out_of_bounds():
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=None, nav1_fromto_raw=0.0)
    assert result == "OUT OF BOUNDS"


def test_weak_signal_returns_no_signal():
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=WEAK, nav1_fromto_raw=0.0)
    assert result == "NO SIGNAL"


def test_strong_signal_returns_status_string():
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=STRONG, nav1_fromto_raw=1.0)
    assert result.startswith("signal=")
    assert "nav1_fromto=1" in result


# ---------------------------------------------------------------------------
# Boundary: strength exactly at threshold is treated as strong (>= is not <)
# ---------------------------------------------------------------------------

def test_strength_exactly_at_threshold_is_not_weak():
    """strength == SIGNAL_THRESHOLD should follow the strong-signal path."""
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=config.SIGNAL_THRESHOLD, nav1_fromto_raw=2.0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 2.0) < 1e-5, (
        f"strength at threshold should pass through nav1_fromto_raw, got {val}"
    )
    assert result != "NO SIGNAL"


def test_strength_just_below_threshold_is_weak():
    """strength just below SIGNAL_THRESHOLD should follow the weak-signal path."""
    sock = MagicMock()
    just_below = config.SIGNAL_THRESHOLD - 0.001
    result = apply_nav1_state(sock, XPLANE, strength=just_below, nav1_fromto_raw=2.0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, (
        f"strength just below threshold should force nav1_fromto=0.0, got {val}"
    )
    assert result == "NO SIGNAL"
