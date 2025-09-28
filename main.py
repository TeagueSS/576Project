"""Main entry point for IoT MQTT simulation GUI."""

from __future__ import annotations

from gui import launch_app
from sim.config_factory import make_config


if __name__ == "__main__":
    launch_app(make_config)


