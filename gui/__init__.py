"""GUI package for IoT MQTT simulation."""

from gui.app import IoTMQTTApp


def launch_app(config_factory):
    import tkinter as tk

    root = tk.Tk()
    root.title("IoT MQTT Simulation")
    root.geometry("1280x720")
    root.minsize(1100, 650)
    IoTMQTTApp(root, config_factory)
    root.mainloop()

__all__ = ["IoTMQTTApp"]


