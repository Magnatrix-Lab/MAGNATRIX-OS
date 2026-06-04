"""CRC Calculator - Cyclic redundancy check for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass
class CRCCalculator:
    polynomial: int = 0x1021

    def calculate(self, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000: crc = (crc << 1) ^ self.polynomial
                else: crc <<= 1
                crc &= 0xFFFF
        return crc

    def verify(self, data: bytes, expected_crc: int) -> bool:
        return self.calculate(data) == expected_crc

    def stats(self, data: bytes) -> dict:
        return {"crc": hex(self.calculate(data)), "length": len(data)}

def run():
    crc = CRCCalculator()
    data = b"hello world"
    print("CRC:", hex(crc.calculate(data)))
    print("Verify:", crc.verify(data, crc.calculate(data)))
    print("Stats:", crc.stats(data))

if __name__ == "__main__": run()
