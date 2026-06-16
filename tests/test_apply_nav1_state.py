import struct
import pytest
from unittest.mock import MagicMock

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
    results = []
    for c in sock.sendto.call_args_list:
        packet = c.args[0]
        (value,) = struct.unpack_from("<f", packet, 5)
        dataref = packet[9:509].rstrip(b"\x00").decode()
        results.append((dataref, value))
    return results


def sent_value_for(sock, dataref):
    matches = [(dr, val) for dr, val in sent_packets(sock) if dr == dataref]
    if not matches:
        raise KeyError(f"dataref {dataref!r} was never sent")
    return matches[-1][1]


def was_sent(sock, dataref):
    return any(dr == dataref for dr, _ in sent_packets(sock))


# ---------------------------------------------------------------------------
# nav1_fromto pass-through under strong signal
# ---------------------------------------------------------------------------

def test_strong_signal_fromto_1_sends_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, fromto=1)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 1.0) < 1e-5, f"expected nav1_fromto=1.0, got {val}"


def test_strong_signal_fromto_2_sends_2():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, fromto=2)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 2.0) < 1e-5, f"expected nav1_fromto=2.0, got {val}"


def test_strong_signal_fromto_0_sends_0():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, fromto=0)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, f"expected nav1_fromto=0.0, got {val}"


# ---------------------------------------------------------------------------
# Weak signal forces nav1_fromto=0.0 regardless of fromto
# ---------------------------------------------------------------------------

def test_weak_signal_fromto_overridden_to_0_when_fromto_is_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, fromto=1)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, f"weak signal should force nav1_fromto=0.0, got {val}"


def test_weak_signal_fromto_overridden_to_0_when_fromto_is_2():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, fromto=2)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, f"weak signal should force nav1_fromto=0.0, got {val}"


# ---------------------------------------------------------------------------
# Out of bounds (strength=None)
# ---------------------------------------------------------------------------

def test_out_of_bounds_sends_override_0():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=None, fromto=1)
    val = sent_value_for(sock, config.DREF_OVERRIDE_NAV)
    assert abs(val - 0.0) < 1e-5, f"out-of-bounds should release override (0.0), got {val}"


def test_out_of_bounds_does_not_send_nav1_fromto():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=None, fromto=1)
    assert not was_sent(sock, config.DREF_NAV1_FROMTO), "out-of-bounds must not write nav1_fromto"


# ---------------------------------------------------------------------------
# Override and flag_gs under strong vs weak signal
# ---------------------------------------------------------------------------

def test_strong_signal_sends_override_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, fromto=1)
    val = sent_value_for(sock, config.DREF_OVERRIDE_NAV)
    assert abs(val - 1.0) < 1e-5, f"strong signal should hold override at 1.0, got {val}"


def test_strong_signal_sends_flag_gs_0():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, fromto=1)
    val = sent_value_for(sock, config.DREF_NAV1_FLAG_GS)
    assert abs(val - 0.0) < 1e-5, f"strong signal should clear GS flag (0.0), got {val}"


def test_weak_signal_sends_override_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, fromto=0)
    val = sent_value_for(sock, config.DREF_OVERRIDE_NAV)
    assert abs(val - 1.0) < 1e-5, f"weak (in-bounds) signal should keep override at 1.0, got {val}"


def test_weak_signal_sends_flag_gs_1():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=WEAK, fromto=0)
    val = sent_value_for(sock, config.DREF_NAV1_FLAG_GS)
    assert abs(val - 1.0) < 1e-5, f"weak signal should raise GS flag (1.0), got {val}"


# ---------------------------------------------------------------------------
# Packet bytes match pack_dref_set (end-to-end encoding check)
# ---------------------------------------------------------------------------

def test_strong_signal_packet_bytes_match_pack_dref_set():
    sock = MagicMock()
    apply_nav1_state(sock, XPLANE, strength=STRONG, fromto=1)
    expected = pack_dref_set(config.DREF_NAV1_FROMTO, 1.0)
    actual_packets = [c.args[0] for c in sock.sendto.call_args_list]
    assert expected in actual_packets, "raw bytes for nav1_fromto=1.0 not found in sent packets"


# ---------------------------------------------------------------------------
# Return-value strings
# ---------------------------------------------------------------------------

def test_out_of_bounds_returns_out_of_bounds():
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=None, fromto=0)
    assert result == "OUT OF BOUNDS"


def test_weak_signal_returns_no_signal():
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=WEAK, fromto=0)
    assert result == "NO SIGNAL"


def test_strong_signal_returns_status_string():
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=STRONG, fromto=1)
    assert result.startswith("signal=")
    assert "nav1_fromto=1" in result


# ---------------------------------------------------------------------------
# Boundary: strength exactly at threshold is strong (condition is <, not <=)
# ---------------------------------------------------------------------------

def test_strength_exactly_at_threshold_is_not_weak():
    sock = MagicMock()
    result = apply_nav1_state(sock, XPLANE, strength=config.SIGNAL_THRESHOLD, fromto=2)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 2.0) < 1e-5, f"strength at threshold should pass through fromto, got {val}"
    assert result != "NO SIGNAL"


def test_strength_just_below_threshold_is_weak():
    sock = MagicMock()
    just_below = config.SIGNAL_THRESHOLD - 0.001
    result = apply_nav1_state(sock, XPLANE, strength=just_below, fromto=2)
    val = sent_value_for(sock, config.DREF_NAV1_FROMTO)
    assert abs(val - 0.0) < 1e-5, f"strength just below threshold should force nav1_fromto=0.0, got {val}"
    assert result == "NO SIGNAL"
