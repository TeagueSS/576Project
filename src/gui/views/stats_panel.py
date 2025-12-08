import tkinter as tk
from tkinter import ttk

class StatsPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame", padding=15)

        # Title
        ttk.Label(self, text="Real-Time Metrics", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))

        # Grid for cards
        self.grid_frame = ttk.Frame(self, style="Card.TFrame")
        self.grid_frame.pack(fill=tk.X)
        self.grid_frame.columnconfigure(0, weight=1)
        self.grid_frame.columnconfigure(1, weight=1)

        # Metrics Data
        self.metrics_labels = {
            "Delivery Ratio": tk.StringVar(value="0.0 %"),
            "Avg Latency": tk.StringVar(value="0 ms"),
            "Duplicates": tk.StringVar(value="0"),
            "Energy (J)": tk.StringVar(value="0.0"),
        }

        # Create 2x2 Grid of Stat Cards
        self._create_stat_card(0, 0, "Delivery Ratio", self.metrics_labels["Delivery Ratio"], "#2ECC71")
        self._create_stat_card(0, 1, "Avg Latency", self.metrics_labels["Avg Latency"], "#3498DB")
        self._create_stat_card(1, 0, "Duplicates", self.metrics_labels["Duplicates"], "#E67E22")
        self._create_stat_card(1, 1, "Energy (J)", self.metrics_labels["Energy (J)"], "#9B59B6")

    def _create_stat_card(self, r, c, title, variable, accent):
        # Mini Card
        f = tk.Frame(self.grid_frame, bg="#F9F9F9", padx=10, pady=10, relief="flat")
        f.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)

        # Color bar on left
        bar = tk.Frame(f, bg=accent, width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        # Text
        content = tk.Frame(f, bg="#F9F9F9")
        content.pack(side=tk.LEFT, fill=tk.BOTH)

        tk.Label(content, text=title, bg="#F9F9F9", fg="#7f8c8d", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(content, textvariable=variable, bg="#F9F9F9", fg="#2c3e50", font=("Segoe UI", 14, "bold")).pack(anchor="w")

    def update_metrics(self, metrics_collector):
        data = metrics_collector.summary()
        ratio = data.get("delivery_ratio", 0) * 100
        latency = data.get("avg_latency", 0) * 1000
        dupes = data.get("duplicates", 0)
        energy = data.get("total_energy_j", 0)

        self.metrics_labels["Delivery Ratio"].set(f"{ratio:.1f} %")
        self.metrics_labels["Avg Latency"].set(f"{latency:.1f} ms")
        self.metrics_labels["Duplicates"].set(str(dupes))
        self.metrics_labels["Energy (J)"].set(f"{energy:.1f}")