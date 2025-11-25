import tkinter as tk
from tkinter import ttk


class TopBar(ttk.Frame):
    def __init__(self, parent, on_run, on_pause, on_speed):
        super().__init__(parent, relief="raised")

        # --- File Operations (Left) ---
        self.btn_load = ttk.Button(self, text="📂 Load Scenario")
        self.btn_load.pack(side=tk.LEFT, padx=5, pady=5)

        self.btn_save = ttk.Button(self, text="💾 Save Results")
        self.btn_save.pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        # --- Playback Controls (Center-ish) ---
        self.btn_run = ttk.Button(self, text="▶ Run", command=on_run)
        self.btn_run.pack(side=tk.LEFT, padx=2)

        self.btn_pause = ttk.Button(self, text="⏸ Pause", command=on_pause)
        self.btn_pause.pack(side=tk.LEFT, padx=2)

        # --- Speed Control ---
        ttk.Label(self, text="Speed:").pack(side=tk.LEFT, padx=(20, 5))

        # FIX: Moved width control to 'length' argument in constructor, removed 'width' from pack()
        self.speed_scale = ttk.Scale(self, from_=0.1, to=10.0, orient=tk.HORIZONTAL, command=on_speed, length=150)
        self.speed_scale.set(1.0)
        self.speed_scale.pack(side=tk.LEFT, padx=5)

        # --- Simulation Status/Title (Right) ---
        ttk.Label(self, text="Scenario: Mesh Failover (E3)", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=15)