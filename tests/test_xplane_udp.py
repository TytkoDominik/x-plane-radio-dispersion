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
