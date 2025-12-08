import tkinter as tk
from tkinter import ttk


class NodePalette(ttk.Frame):
    def __init__(self, parent, on_node_type_selected, on_simulation_type_changed):
        super().__init__(parent, style="Card.TFrame", padding=15)
        self.on_select = on_node_type_selected
        self.on_sim_change = on_simulation_type_changed

        # Header
        ttk.Label(self, text="Simulation Setup", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))

        # 1. Experiment Selector
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

        cb = ttk.Combobox(self, textvariable=self.sim_type_var, values=sim_types, state="readonly", height=10)
        cb.pack(fill="x", pady=(0, 10))
        cb.bind("<<ComboboxSelected>>", self._on_sim_change)

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)

        ttk.Label(self, text="Drag & Drop Nodes:", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                                                                           pady=(0, 5))

        # 2. Scrollable List
        list_frame = ttk.Frame(self, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_frame, height=220, bg="#FFFFFF", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style="Card.TFrame")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw",
                                  width=320)  # Width fix ensures fill
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Initial Load
        self.refresh_node_options(self.sim_type_var.get())

    def refresh_node_options(self, experiment_mode):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        mode = experiment_mode.lower()

        # Always allow Gateway
        self._add_node_option("Gateway", "Base Station", "#8e44ad")

        # Filter logic
        if "zigbee" in mode or "e1" in mode:
            self._add_node_option("Sensor", "IoT Node", "#27ae60")
            self._add_node_option("Asset Tag", "Mobile Tracker", "#16a085")
        elif "wi-fi" in mode or "wifi" in mode:
            self._add_node_option("Laptop", "High Traffic", "#e67e22")
            self._add_node_option("iPhone", "Roaming Mobile", "#2980b9")
        elif "ble" in mode:
            self._add_node_option("Beacon", "Stationary Ref", "#f1c40f")
            self._add_node_option("Wearable", "Fitness Tracker", "#d35400")
        elif "ad-hoc" in mode:
            self._add_node_option("Source Node", "Sender", "#2ecc71")
            self._add_node_option("Sink Node", "Receiver", "#e74c3c")
            self._add_node_option("Ad-Hoc Relay", "Repeater", "#7f8c8d")
        else:
            self._add_node_option("Sensor", "IoT Node", "#27ae60")
            self._add_node_option("iPhone", "Roaming Mobile", "#2980b9")
            self._add_node_option("Laptop", "High Traffic", "#e67e22")

    def _add_node_option(self, name, desc, color):
        # Card style button
        card = tk.Frame(self.scrollable_frame, bg="#fdfdfd", bd=1, relief="solid")
        card.pack(fill="x", padx=2, pady=3)
        # remove ugly border color, make it light gray
        card.config(highlightbackground="#ecf0f1", highlightthickness=1, bd=0)

        # Color stripe
        stripe = tk.Frame(card, bg=color, width=5)
        stripe.pack(side=tk.LEFT, fill=tk.Y)

        # Text
        txt_frame = tk.Frame(card, bg="#fdfdfd")
        txt_frame.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=5)

        lbl = tk.Label(txt_frame, text=name, font=("Segoe UI", 10, "bold"), bg="#fdfdfd", fg="#2c3e50")
        lbl.pack(anchor="w")

        desc_lbl = tk.Label(txt_frame, text=desc, font=("Segoe UI", 8), bg="#fdfdfd", fg="#95a5a6")
        desc_lbl.pack(anchor="w")

        # Bindings for entire card
        for w in [card, stripe, txt_frame, lbl, desc_lbl]:
            w.bind("<Button-1>", lambda e, n=name: self._on_click(n))
            w.bind("<Enter>", lambda e, c=card: c.config(bg="#f0f3f4"))
            w.bind("<Leave>", lambda e, c=card: c.config(bg="#fdfdfd"))

    def _on_click(self, node_type):
        self.on_select(node_type)

    def _on_sim_change(self, event):
        selected = self.sim_type_var.get()
        self.refresh_node_options(selected)
        self.on_sim_change(selected)