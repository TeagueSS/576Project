"""Exports BLE, Wi-Fi, and Zigbee radio profiles (PHY + MAC basics)."""

from .wifi import WifiRadio
from .ble import BleRadio
from .zigbee import ZigbeeRadio
import yaml
import os


# Load configs once
def load_config(name):
    path = os.path.join(os.path.dirname(__file__), f"../configs/{name}.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f)


RADIOS = {
    "wifi": (WifiRadio, load_config("wifi")),
    "ble": (BleRadio, load_config("ble")),
    "zigbee": (ZigbeeRadio, load_config("zigbee")),
}


def create_radio(name, env):
    cls, cfg = RADIOS.get(name.lower(), (WifiRadio, load_config("wifi")))
    return cls(env, cfg)
