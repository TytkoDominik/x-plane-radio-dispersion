import struct
from typing import List, Tuple

def pack_rref_subscribe(index: int, dataref: str, freq: int = 10) -> bytes:
    dref_bytes = dataref.encode().ljust(400, b"\x00")[:400]
    return struct.pack("<4sxii400s", b"RREF", freq, index, dref_bytes)

def pack_dref_set(dataref: str, value: float) -> bytes:
    dref_bytes = dataref.encode().ljust(500, b"\x00")[:500]
    return struct.pack("<4sxf500s", b"DREF", value, dref_bytes)

def parse_rref_response(data: bytes) -> List[Tuple[int, float]]:
    if len(data) < 5 or data[:4] != b"RREF":
        return []
    results = []
    offset = 5
    while offset + 8 <= len(data):
        index, value = struct.unpack_from("<if", data, offset)
        results.append((index, value))
        offset += 8
    return results
