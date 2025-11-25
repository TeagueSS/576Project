import tkinter as tk
from tkinter import ttk


class NodePalette(ttk.LabelFrame):
    def __init__(self, parent, on_node_type_selected):
        super().__init__(parent, text="Node Types (Palette)")
        self.on_select = on_node_type_selected

        # Scrollable canvas setup (standard tkinter pattern)
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # --- Add Pre-Fab Node Types ---
        self._add_node_option("Gateway", "strong_node.png", "Main Router\nHigh Power")
        self._add_node_option("Sensor", "sensor.png", "Temp/Humid\nLow Power")
        self._add_node_option("iPhone", "mobile.png", "Mobile Client\nRandom Walk")
        self._add_node_option("Laptop", "laptop.png", "Stationary\nHigh Traffic")

    def _add_node_option(self, name, icon_path, desc):
        """Creates a clickable card for a node type."""
        card = ttk.Frame(self.scrollable_frame, relief="raised", borderwidth=1)
        card.pack(fill="x", padx=5, pady=5)

        # Title
        lbl = ttk.Label(card, text=name, font=("Helvetica", 11, "bold"))
        lbl.pack(anchor="w", padx=5, pady=(5, 0))

        # Description
        desc_lbl = ttk.Label(card, text=desc, font=("Helvetica", 9), foreground="#555")
        desc_lbl.pack(anchor="w", padx=5, pady=(0, 5))

        # Interaction (Make whole card clickable)
        for widget in [card, lbl, desc_lbl]:
            widget.bind("<Button-1>", lambda e, n=name: self._on_click(n))

    def _on_click(self, node_type):
        print(f"Palette Selected: {node_type}")
        self.on_select(node_type)