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
    strength = smap.lookup(lon=12.8928, lat=48.0026)
    assert isinstance(strength, float)
    assert 0.0 <= strength <= 1.0

def test_outside_bounds_returns_zero(smap):
    assert smap.lookup(lon=0.0, lat=0.0) == 0.0

def test_transparent_pixel_returns_zero(smap):
    strength = smap.lookup(lon=smap.west, lat=smap.north)
    assert strength == 0.0

def test_strong_signal_near_transmitter(smap):
    strength = smap.lookup(lon=12.8928, lat=48.0026)
    assert strength > 0.5
