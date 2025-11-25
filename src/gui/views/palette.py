import tkinter as tk
from tkinter import ttk


class NodePalette(ttk.LabelFrame):
    def __init__(self, parent, on_node_type_selected, on_simulation_type_changed):
        super().__init__(parent, text="Simulation & Nodes")
        self.on_select = on_node_type_selected
        self.on_sim_change = on_simulation_type_changed

        # --- 1. Simulation Type Selector ---
        sim_frame = ttk.Frame(self)
        sim_frame.pack(fill="x", padx=5, pady=10)

        ttk.Label(sim_frame, text="Experiment Type:", font=("Arial", 10, "bold")).pack(anchor="w")

        self.sim_type_var = tk.StringVar(value="E3: Topology Failover")
        sim_types = [
            "E1: Duty Cycle Study",
            "E2: Protocol Compare",
            "E3: Topology Failover",
            "Protocol: Zigbee Only",
            "Protocol: Wi-Fi Only",
            "Protocol: BLE Only",
            "Ad-Hoc Mesh (Source->Sink)"
        ]

        self.sim_combo = ttk.Combobox(sim_frame, textvariable=self.sim_type_var, values=sim_types, state="readonly")
        self.sim_combo.pack(fill="x", pady=5)
        self.sim_combo.bind("<<ComboboxSelected>>", self._on_sim_change)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=5, pady=5)

        # --- 2. Scrollable Node List ---
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_frame)
        self.scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # --- Infrastructure Nodes ---
        self._add_header("Infrastructure")
        self._add_node_option("Gateway", "Main Router\nHigh Power")

        # --- Ad-Hoc Specific ---
        self._add_header("Ad-Hoc / Mesh")
        self._add_node_option("Source Node", "Start Point\n(Ad-Hoc Sender)")
        self._add_node_option("Sink Node", "End Point\n(Ad-Hoc Receiver)")
        self._add_node_option("Ad-Hoc Relay", "Mesh Relay\nForwarder")

        # --- End Devices ---
        self._add_header("End Devices")
        self._add_node_option("Sensor", "Temp/Humid\nLow Power")
        self._add_node_option("iPhone", "Mobile Client\nRandom Walk")
        self._add_node_option("Laptop", "Stationary\nHigh Traffic")

    def _add_header(self, text):
        f = ttk.Frame(self.scrollable_frame)
        f.pack(fill="x", padx=2, pady=(10, 2))
        ttk.Label(f, text=text, font=("Arial", 9, "bold", "italic"), foreground="#333").pack(anchor="w")
        ttk.Separator(f, orient="horizontal").pack(fill="x")

    def _add_node_option(self, name, desc):
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
        self.on_select(node_type)

    def _on_sim_change(self, event):
        selected = self.sim_type_var.get()
        self.on_sim_change(selected)