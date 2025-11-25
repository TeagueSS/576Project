"""Summary cards for delivery ratio, latency, duplicates, and energy."""
import tkinter as tk
from tkinter import ttk


class StatsPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Define metrics to display
        self.metrics_labels = {
            "Delivery Ratio": tk.StringVar(value="0.0 %"),
            "Avg Latency": tk.StringVar(value="0 ms"),
            "Duplicates": tk.StringVar(value="0"),
            "Total Energy": tk.StringVar(value="0.0 J"),
            "Active Nodes": tk.StringVar(value="0"),
        }

        # Create Layout
        row = 0
        for label, var in self.metrics_labels.items():
            ttk.Label(self, text=f"{label}:", font=("Helvetica", 10, "bold")).grid(row=row, column=0, sticky="w",
                                                                                   padx=10, pady=2)
            ttk.Label(self, textvariable=var, font=("Helvetica", 10)).grid(row=row, column=1, sticky="e", padx=10,
                                                                           pady=2)
            row += 1

    def update_metrics(self, metrics_collector):
        """
        Updates UI from the MetricsCollector object.
        """
        # Get raw data
        data = metrics_collector.summary()

        # Format and set
        ratio = data.get("delivery_ratio", 0) * 100
        latency = data.get("avg_latency", 0) * 1000  # convert s to ms
        dupes = data.get("duplicates", 0)
        energy = data.get("total_energy_j", 0)

        self.metrics_labels["Delivery Ratio"].set(f"{ratio:.1f} %")
        self.metrics_labels["Avg Latency"].set(f"{latency:.1f} ms")
        self.metrics_labels["Duplicates"].set(str(dupes))
        self.metrics_labels["Total Energy"].set(f"{energy:.2f} J")