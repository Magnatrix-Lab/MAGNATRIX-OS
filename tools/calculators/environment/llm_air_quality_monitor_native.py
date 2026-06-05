"""Air Quality Monitor — AQI, pollutant tracking, alerts, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class AirQualityMonitor:
    def __init__(self):
        self.readings: List[Dict] = []
        self.stations: Dict[str, Dict] = {}
        self.alerts: List[Dict] = []

    def add_station(self, station_id: str, lat: float, lon: float):
        self.stations[station_id] = {"lat": lat, "lon": lon, "latest": None}

    def add_reading(self, station_id: str, pm25: float, pm10: float, o3: float, no2: float, co: float, so2: float = 0):
        reading = {"station": station_id, "pm25": pm25, "pm10": pm10, "o3": o3, "no2": no2, "co": co, "so2": so2}
        self.readings.append(reading)
        if station_id in self.stations:
            self.stations[station_id]["latest"] = reading
        aqi = self._calculate_aqi(pm25, pm10, o3, no2, co, so2)
        if aqi > 100:
            self.alerts.append({"station": station_id, "aqi": aqi, "level": "UNHEALTHY" if aqi > 150 else "MODERATE"})

    def _calculate_aqi(self, pm25, pm10, o3, no2, co, so2):
        # Simplified AQI from PM2.5
        if pm25 <= 12:
            return pm25 * 50 / 12
        elif pm25 <= 35.4:
            return 50 + (pm25 - 12) * 50 / 23.4
        elif pm25 <= 55.4:
            return 100 + (pm25 - 35.4) * 50 / 20
        elif pm25 <= 150.4:
            return 150 + (pm25 - 55.4) * 50 / 95
        else:
            return 200 + (pm25 - 150.4) * 100 / 100

    def average_aqi(self, station_id: str = None) -> float:
        if station_id:
            vals = [self._calculate_aqi(r["pm25"], r["pm10"], r["o3"], r["no2"], r["co"], r["so2"]) for r in self.readings if r["station"] == station_id]
        else:
            vals = [self._calculate_aqi(r["pm25"], r["pm10"], r["o3"], r["no2"], r["co"], r["so2"]) for r in self.readings]
        return sum(vals) / len(vals) if vals else 0

    def stats(self) -> Dict:
        return {"stations": len(self.stations), "readings": len(self.readings), "alerts": len(self.alerts)}

def run():
    aqm = AirQualityMonitor()
    aqm.add_station("S1", 40.7, -74.0)
    aqm.add_reading("S1", 45, 60, 80, 30, 5)
    aqm.add_reading("S1", 15, 25, 40, 20, 3)
    print("Avg AQI:", aqm.average_aqi("S1"))
    print(aqm.stats())

if __name__ == "__main__":
    run()
