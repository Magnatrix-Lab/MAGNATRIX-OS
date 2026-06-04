"""Serial Protocol — UART/SPI/I2C abstraction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import time
import queue

class SerialMode(Enum):
    UART = auto()
    SPI = auto()
    I2C = auto()

@dataclass
class SerialFrame:
    frame_id: int
    data: List[int]
    checksum: int
    timestamp: float

    def validate(self) -> bool:
        return sum(self.data) & 0xFF == self.checksum

class SerialProtocol:
    def __init__(self, mode: SerialMode = SerialMode.UART, baudrate: int = 9600):
        self.mode = mode
        self.baudrate = baudrate
        self.tx_buffer: List[SerialFrame] = []
        self.rx_buffer: List[SerialFrame] = []
        self.transmitted: List[SerialFrame] = []
        self.received: List[SerialFrame] = []

    def create_frame(self, data: List[int]) -> SerialFrame:
        checksum = sum(data) & 0xFF
        return SerialFrame(len(self.transmitted), data, checksum, time.time())

    def transmit(self, data: List[int]) -> SerialFrame:
        frame = self.create_frame(data)
        self.tx_buffer.append(frame)
        self.transmitted.append(frame)
        return frame

    def receive(self, data: List[int], checksum: int) -> SerialFrame:
        frame = SerialFrame(len(self.received), data, checksum, time.time())
        self.rx_buffer.append(frame)
        self.received.append(frame)
        return frame

    def read_rx(self) -> Optional[SerialFrame]:
        if self.rx_buffer:
            return self.rx_buffer.pop(0)
        return None

    def get_valid_rx(self) -> List[SerialFrame]:
        return [f for f in self.rx_buffer if f.validate()]

    def stats(self) -> Dict:
        return {"mode": self.mode.name, "baudrate": self.baudrate, "tx": len(self.transmitted), "rx": len(self.received), "valid_rx": len(self.get_valid_rx())}

def run():
    serial = SerialProtocol(SerialMode.UART, 115200)
    serial.transmit([0x01, 0x02, 0x03])
    serial.receive([0x01, 0x02, 0x03], 0x06)
    serial.receive([0x01, 0x02, 0x03], 0x07)
    print("Valid RX:", len(serial.get_valid_rx()))
    print(serial.stats())

if __name__ == "__main__":
    run()
