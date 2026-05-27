#!/usr/bin/env python3
"""
MAGNATRIX-OS Mobile Layer Native
Unified mobile layer: push notification, geolocation, camera, sensors.
Pure Python — bridges to native mobile APIs via HTTP/WebSocket.
"""
import json, time, urllib.request, urllib.parse, threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class MobileConfig:
    push_gateway: str = "http://localhost:17000/push"
    location_interval_sec: float = 30.0
    camera_enabled: bool = False
    microphone_enabled: bool = False
    device_id: str = ""


class PushNotificationNative:
    """Push notification sender (FCM/APNs bridge via HTTP)."""

    def __init__(self, config: MobileConfig = None):
        self.config = config or MobileConfig()

    def send(self, device_token: str, title: str, body: str, data: Dict = None) -> bool:
        payload = {
            "to": device_token,
            "notification": {"title": title, "body": body},
            "data": data or {},
        }
        try:
            req = urllib.request.Request(
                self.config.push_gateway,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False


class GeolocationNative:
    """Geolocation tracking via browser/device API bridge."""

    def __init__(self, config: MobileConfig = None):
        self.config = config or MobileConfig()
        self._position: Optional[Dict] = None
        self._watching = False

    def get_current_position(self) -> Optional[Dict]:
        """Return last known position."""
        return self._position

    def watch_position(self, callback=None):
        """Start watching position updates."""
        self._watching = True
        def loop():
            while self._watching:
                # In real impl, gets position from device via WebSocket/bridge
                self._position = {
                    "lat": 0.0, "lon": 0.0,
                    "accuracy": 10.0, "timestamp": time.time(),
                }
                if callback:
                    callback(self._position)
                time.sleep(self.config.location_interval_sec)
        threading.Thread(target=loop, daemon=True).start()

    def stop_watching(self):
        self._watching = False


class CameraNative:
    """Camera access bridge for mobile devices."""

    def __init__(self, config: MobileConfig = None):
        self.config = config or MobileConfig()
        self._stream_url: Optional[str] = None

    def capture_photo(self) -> Optional[str]:
        """Capture photo, return base64 data URI or file path."""
        if not self.config.camera_enabled:
            return None
        # Bridge to device camera via HTTP endpoint
        try:
            req = urllib.request.Request("http://localhost:17000/camera/capture", method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data.get("image_data_uri")
        except Exception:
            return None

    def start_stream(self) -> Optional[str]:
        """Start video stream, return WebSocket URL."""
        if not self.config.camera_enabled:
            return None
        return "ws://localhost:17000/camera/stream"

    def stop_stream(self):
        pass


class SensorNative:
    """Mobile sensor data (accelerometer, gyroscope, proximity)."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._callbacks: List[Callable] = []

    def read(self, sensor_type: str) -> Optional[Dict]:
        """Read sensor value."""
        return self._data.get(sensor_type)

    def watch(self, sensor_type: str, callback):
        """Watch sensor for changes."""
        self._callbacks.append((sensor_type, callback))

    def feed(self, sensor_type: str, value: Dict):
        """Feed sensor data from device bridge."""
        self._data[sensor_type] = value
        for st, cb in self._callbacks:
            if st == sensor_type:
                cb(value)


class MobileLayerNative:
    """Unified mobile layer orchestrator."""

    def __init__(self, config: MobileConfig = None):
        self.config = config or MobileConfig()
        self.push = PushNotificationNative(self.config)
        self.geo = GeolocationNative(self.config)
        self.camera = CameraNative(self.config)
        self.sensor = SensorNative()

    def get_device_info(self) -> Dict:
        return {
            "device_id": self.config.device_id,
            "platform": "unknown",  # Would be detected from user agent
            "push_enabled": True,
            "location_enabled": True,
            "camera_enabled": self.config.camera_enabled,
        }

    def notify(self, title: str, body: str, token: str = "") -> bool:
        return self.push.send(token or "default", title, body)

    def get_location(self) -> Optional[Dict]:
        return self.geo.get_current_position()

    def capture(self) -> Optional[str]:
        return self.camera.capture_photo()


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Mobile Layer Demo")
    print("=" * 60)

    mobile = MobileLayerNative(MobileConfig(device_id="demo-phone-01"))

    print("\n[1] Device info:")
    print(f"    {mobile.get_device_info()}")

    print("\n[2] Push notification:")
    result = mobile.notify("MAGNATRIX", "Mobile layer active")
    print(f"    Sent: {result}")

    print("\n[3] Location:")
    print(f"    {mobile.get_location()}")

    print("\n[4] Camera capture:")
    print(f"    {mobile.capture()}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
