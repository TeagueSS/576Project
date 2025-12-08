import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
from ..sim.environment import SimulationEnvironment
from ..sim.metrics import MetricsCollector
from ..loader import ScenarioLoader
from ..radios import load_config

COLORS = {
    "bg": "#f0f2f5",
    "panel_bg": "#ffffff",
    "header": "#2c3e50",
    "accent": "#3498db",
    "danger": "#e74c3c",
    "success": "#2ecc71",
    "text": "#2c3e50",
    "warn": "#f39c12",
}


class ModernIotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IoT Mesh Network Simulator - CS576")
        self.geometry("1300x850")
        self.configure(bg=COLORS["bg"])
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        self.sim_env = None
        self.metrics = None
        self.loader = None
        self.is_running = False
        self.nodes_data = []
        self.selected_node_id = None
        self.node_mode = tk.StringVar(value="Select")
        self.history = {"latency": [0] * 100, "queue": [0] * 100}

        # PROTOCOL SELECTOR VARIABLE
        self.protocol_var = tk.StringVar(value="Zigbee")

        # SIMULATION SPEED VARIABLE (1.0 = real-time, higher = faster)
        self.sim_speed = tk.DoubleVar(value=1.0)

        # Load protocol ranges directly from config files so circles stay accurate
        self.protocol_ranges = {
            "zigbee": load_config("zigbee").get("range_m", 30),
            "ble": load_config("ble").get("range_m", 50),
            "wifi": load_config("wifi").get("range_m", 120),
        }

        self._build_layout()
        self.reset_simulation()
        self.after(100, self.update_loop)

    def _configure_styles(self):
        self.style.configure("TFrame", background=COLORS["bg"])
        self.style.configure(
            "Card.TFrame", background=COLORS["panel_bg"], relief="flat"
        )
        self.style.configure(
            "Header.TLabel",
            font=("Segoe UI", 12, "bold"),
            background=COLORS["panel_bg"],
            foreground=COLORS["header"],
        )
        self.style.configure(
            "Stat.TLabel",
            font=("Segoe UI", 20, "bold"),
            background=COLORS["panel_bg"],
            foreground=COLORS["accent"],
        )
        self.style.configure(
            "StatLabel.TLabel",
            font=("Segoe UI", 9),
            background=COLORS["panel_bg"],
            foreground="#7f8c8d",
        )
        self.style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="white",
            font=("Segoe UI", 9, "bold"),
        )
        self.style.configure(
            "Danger.TButton",
            background=COLORS["danger"],
            foreground="white",
            font=("Segoe UI", 9, "bold"),
        )

    def _build_layout(self):
        # Toolbar
        toolbar = ttk.Frame(self, style="Card.TFrame", padding=10)
        toolbar.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(
            toolbar,
            text="CONTROLS",
            font=("Segoe UI", 10, "bold"),
            background=COLORS["panel_bg"],
        ).pack(side=tk.LEFT, padx=10)
        self.btn_run = ttk.Button(
            toolbar, text="▶ START", style="Accent.TButton", command=self.toggle_run
        )
        self.btn_run.pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="↻ RESET", command=self.reset_simulation).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=15
        )

        # PROTOCOL SELECTOR
        ttk.Label(
            toolbar,
            text="PROTOCOL:",
            background=COLORS["panel_bg"],
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(5, 0))
        proto_cb = ttk.Combobox(
            toolbar,
            textvariable=self.protocol_var,
            values=["Zigbee", "Wi-Fi", "BLE"],
            state="readonly",
            width=10,
        )
        proto_cb.pack(side=tk.LEFT, padx=5)
        proto_cb.bind("<<ComboboxSelected>>", lambda e: self.reset_simulation())

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=15
        )

        # SIMULATION SPEED SLIDER
        ttk.Label(
            toolbar,
            text="SPEED:",
            background=COLORS["panel_bg"],
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(5, 0))

        self.speed_slider = ttk.Scale(
            toolbar,
            from_=0.1,
            to=10.0,
            orient=tk.HORIZONTAL,
            variable=self.sim_speed,
            length=100,
        )
        self.speed_slider.pack(side=tk.LEFT, padx=5)

        self.lbl_speed = ttk.Label(
            toolbar,
            text="1.0x",
            background=COLORS["panel_bg"],
            font=("Segoe UI", 9, "bold"),
            width=5,
        )
        self.lbl_speed.pack(side=tk.LEFT, padx=(0, 10))

        # Update speed label when slider moves
        self.sim_speed.trace_add("write", self._update_speed_label)

        self.lbl_broker_status = ttk.Label(
            toolbar,
            text="● BROKER ONLINE",
            foreground=COLORS["success"],
            background=COLORS["panel_bg"],
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_broker_status.pack(side=tk.LEFT, padx=20)

        ttk.Button(
            toolbar,
            text="☠️ FAILOVER",
            style="Danger.TButton",
            command=self.trigger_failover,
        ).pack(side=tk.RIGHT, padx=10)

        # Main Panes
        main_pane = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, bg=COLORS["bg"], sashwidth=6
        )
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Map
        map_frame = ttk.Frame(main_pane, style="Card.TFrame")
        main_pane.add(map_frame, minsize=600, width=800)
        map_tools = ttk.Frame(map_frame, style="Card.TFrame", padding=5)
        map_tools.pack(fill=tk.X)
        for text, mode in [
            ("🖱 Select", "Select"),
            ("📍 Sensor", "Sensor"),
            ("📱 Mobile", "Mobile"),
            ("📡 Gateway", "Gateway"),
        ]:
            ttk.Radiobutton(
                map_tools, text=text, variable=self.node_mode, value=mode
            ).pack(side=tk.LEFT, padx=10)

        self.fig_map = Figure(figsize=(5, 5), dpi=100)
        self.fig_map.patch.set_facecolor(COLORS["panel_bg"])
        self.ax_map = self.fig_map.add_subplot(111)
        self.canvas_map = FigureCanvasTkAgg(self.fig_map, master=map_frame)
        self.canvas_map.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas_map.mpl_connect("button_press_event", self.on_map_click)

        # Right: Stats
        sidebar = ttk.Frame(main_pane, style="TFrame")
        main_pane.add(sidebar, minsize=350)

        stats_frame = ttk.Frame(sidebar, style="Card.TFrame", padding=15)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        sf_grid = ttk.Frame(stats_frame, style="Card.TFrame")
        sf_grid.pack(fill=tk.X)
        self.lbl_delivery = self._make_stat_box(sf_grid, 0, 0, "Delivery Ratio", "0%")
        self.lbl_energy = self._make_stat_box(sf_grid, 0, 1, "Total Energy", "0 J")
        self.lbl_latency = self._make_stat_box(sf_grid, 1, 0, "Avg Latency", "0 ms")
        self.lbl_dupes = self._make_stat_box(sf_grid, 1, 1, "Duplicates", "0")

        nb = ttk.Notebook(sidebar)
        nb.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        t1 = ttk.Frame(nb, style="Card.TFrame")
        nb.add(t1, text="📈 Global Queue")
        self.fig_q = Figure(figsize=(4, 2), dpi=80)
        self.ax_q = self.fig_q.add_subplot(111)
        self.canvas_q = FigureCanvasTkAgg(self.fig_q, master=t1)
        self.canvas_q.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=10)

        t2 = ttk.Frame(nb, style="Card.TFrame")
        nb.add(t2, text="📊 Topic Heatmap")
        self.fig_h = Figure(figsize=(4, 2), dpi=80)
        self.ax_h = self.fig_h.add_subplot(111)
        self.canvas_h = FigureCanvasTkAgg(self.fig_h, master=t2)
        self.canvas_h.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=10)

        # Node Status Table
        self.inspector = ttk.Frame(sidebar, style="Card.TFrame", padding=10)
        self.inspector.pack(fill=tk.BOTH, expand=True, side=tk.BOTTOM)

        ttk.Label(
            self.inspector,
            text="NODE STATUS",
            font=("Segoe UI", 10, "bold"),
            background=COLORS["panel_bg"],
        ).pack(anchor="w", pady=(0, 5))

        # Scrollable table frame
        table_frame = ttk.Frame(self.inspector, style="Card.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview with columns
        columns = ("ID", "Type", "State", "Battery")
        self.node_table = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=6, selectmode="browse"
        )

        # Configure columns
        self.node_table.heading("ID", text="ID")
        self.node_table.heading("Type", text="Type")
        self.node_table.heading("State", text="State")
        self.node_table.heading("Battery", text="Battery")

        self.node_table.column("ID", width=80, anchor="w")
        self.node_table.column("Type", width=60, anchor="center")
        self.node_table.column("State", width=80, anchor="center")
        self.node_table.column("Battery", width=60, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.node_table.yview)
        self.node_table.configure(yscrollcommand=scrollbar.set)

        self.node_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection event
        self.node_table.bind("<<TreeviewSelect>>", self._on_table_select)

        # Configure row tags for coloring
        self.node_table.tag_configure("active", background="#d5f4e6")
        self.node_table.tag_configure("disconnected", background="#fadbd8")
        self.node_table.tag_configure("broker_down", background="#fadbd8")
        self.node_table.tag_configure("dead", background="#d5d8dc")

        # Action buttons frame
        btn_frame = ttk.Frame(self.inspector, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        self.btn_disc = ttk.Button(
            btn_frame,
            text="Disconnect",
            command=self.disconnect_node,
            state="disabled",
        )
        self.btn_disc.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_del = ttk.Button(
            btn_frame, text="Delete", command=self.delete_node, state="disabled"
        )
        self.btn_del.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

    def _make_stat_box(self, p, r, c, t, d):
        f = ttk.Frame(p, style="Card.TFrame", padding=5)
        f.grid(row=r, column=c, sticky="ew")
        p.columnconfigure(c, weight=1)
        ttk.Label(f, text=t, style="StatLabel.TLabel").pack(anchor="w")
        l = ttk.Label(f, text=d, style="Stat.TLabel")
        l.pack(anchor="w")
        return l

    def reset_simulation(self):
        self.is_running = False
        self.btn_run.config(text="▶ START")
        self.sim_env = SimulationEnvironment()
        self.metrics = MetricsCollector()
        self.loader = ScenarioLoader(self.sim_env.env, self.metrics)

        # Load the selected protocol
        proto = self.protocol_var.get()
        self.loader.load_experiment(proto)

        self.nodes_data = self.loader.get_gui_node_data()
        self.history = {"latency": [0] * 100, "queue": [0] * 100}
        self.selected_node_id = None
        self._refresh_inspector()
        self._draw_map()
        self._draw_charts()

    def toggle_run(self):
        self.is_running = not self.is_running
        self.btn_run.config(text="⏸ PAUSE" if self.is_running else "▶ RESUME")

    def _update_speed_label(self, *args):
        """Update the speed display label when slider changes."""
        speed = self.sim_speed.get()
        self.lbl_speed.config(text=f"{speed:.1f}x")

    def trigger_failover(self):
        if self.loader.broker:
            self.sim_env.env.process(self.loader.broker.failover_sequence(10.0))

    def disconnect_node(self):
        if self.selected_node_id:
            n = self.loader.get_node(self.selected_node_id)
            if n:
                n.toggle_connection()
                self._refresh_inspector()

    def delete_node(self):
        if self.selected_node_id:
            self.loader.remove_node(self.selected_node_id)
            self.selected_node_id = None
            self._refresh_inspector()
            self._draw_map()

    def on_map_click(self, event):
        if event.inaxes != self.ax_map:
            return
        if self.node_mode.get() == "Select":
            clicked = None
            for n in self.nodes_data:
                if np.hypot(n["x"] - event.xdata, n["y"] - event.ydata) < 8:
                    clicked = n
                    break
            self.selected_node_id = clicked["id"] if clicked else None

            # Sync table selection with map click
            self.node_table.selection_remove(*self.node_table.selection())
            if self.selected_node_id:
                for item in self.node_table.get_children():
                    if self.node_table.item(item)["values"][0] == self.selected_node_id:
                        self.node_table.selection_set(item)
                        self.node_table.see(item)
                        break

            self._update_buttons()
            self._draw_map()
        else:
            self.loader.add_dynamic_node(self.node_mode.get(), event.xdata, event.ydata)
            self.node_mode.set("Select")
            self.nodes_data = self.loader.get_gui_node_data()
            self._refresh_inspector()
            self._draw_map()

    def _on_table_select(self, event):
        """Handle table row selection."""
        selection = self.node_table.selection()
        if selection:
            item = self.node_table.item(selection[0])
            self.selected_node_id = item["values"][0]
            self._update_buttons()
            self._draw_map()
        else:
            self.selected_node_id = None
            self._update_buttons()

    def _update_buttons(self):
        """Update button states based on selection."""
        if not self.selected_node_id:
            self.btn_disc.config(state="disabled", text="Disconnect")
            self.btn_del.config(state="disabled")
            return

        n = next((x for x in self.nodes_data if x["id"] == self.selected_node_id), None)
        if n:
            self.btn_disc.config(
                state="normal",
                text="Reconnect" if n["state"] == "disconnected" else "Disconnect",
            )
            self.btn_del.config(state="normal")
        else:
            self.selected_node_id = None
            self.btn_disc.config(state="disabled", text="Disconnect")
            self.btn_del.config(state="disabled")

    def _refresh_inspector(self):
        """Refresh the node status table with current data."""
        current_selection = self.selected_node_id

        # Clear existing rows
        for item in self.node_table.get_children():
            self.node_table.delete(item)

        # Populate table with all nodes
        for n in self.nodes_data:
            state = n["state"]
            battery = f"{n['battery']}%"
            tag = state if state in ("active", "disconnected", "broker_down", "dead") else ""

            self.node_table.insert(
                "", "end",
                values=(n["id"], n["type"], state, battery),
                tags=(tag,)
            )

        # Restore selection if it still exists
        if current_selection:
            for item in self.node_table.get_children():
                if self.node_table.item(item)["values"][0] == current_selection:
                    self.node_table.selection_set(item)
                    break

        self._update_buttons()

    def update_loop(self):
        if self.is_running and self.sim_env:
            try:
                # Advance simulation by speed-adjusted time step
                time_step = 0.5 * self.sim_speed.get()
                self.sim_env.run(until=self.sim_env.now + time_step)
                self.nodes_data = self.loader.get_gui_node_data()
                stats = self.metrics.summary()

                self.lbl_delivery.config(
                    text=f"{stats.get('delivery_ratio', 0) * 100:.1f}%"
                )
                self.lbl_energy.config(text=f"{stats.get('total_energy_j', 0):.1f} J")
                self.lbl_latency.config(
                    text=f"{stats.get('avg_latency', 0) * 1000:.1f} ms"
                )
                self.lbl_dupes.config(text=str(stats.get("duplicates", 0)))

                is_alive = self.loader.broker.is_alive
                if is_alive:
                    self.lbl_broker_status.config(
                        text="● BROKER ONLINE", foreground=COLORS["success"]
                    )
                else:
                    self.lbl_broker_status.config(
                        text="● BROKER OFFLINE", foreground=COLORS["danger"]
                    )

                self.history["latency"].append(stats.get("avg_latency", 0) * 1000)
                broker_q = sum(
                    [len(q) for q in self.loader.broker.client_queues.values()]
                )
                client_q = sum(
                    [
                        len(node.mqtt.msg_queue)
                        for node in self.loader.nodes
                        if hasattr(node, "mqtt")
                    ]
                )
                self.history["queue"].append(broker_q + client_q)
                if len(self.history["queue"]) > 100:
                    self.history["queue"].pop(0)
                    self.history["latency"].pop(0)

                # Always refresh table to show state changes
                self._refresh_inspector()
                self._draw_map()
                self._draw_charts()
            except Exception as e:
                print(e)
                self.is_running = False
        self.after(50, self.update_loop)

    def _draw_map(self):
        self.ax_map.clear()
        self.ax_map.axis("off")

        def _norm_proto(p):
            """Normalize protocol names (e.g., 'Wi-Fi' -> 'wifi')."""
            return p.lower().replace("-", "").replace("_", "")

        # Protocol ranges (from config files: zigbee.yaml, ble.yaml, wifi.yaml)
        PROTOCOL_RANGES = self.protocol_ranges

        # Determine active protocol for view scaling
        active_proto = _norm_proto(self.protocol_var.get())
        # Default view and scale
        xlim = ylim = 200
        scale_length = 50
        scale_ticks = [0, 25, 50]
        if active_proto == "wifi":
            xlim = ylim = 240  # give extra space for 120m radius
            scale_length = 100
            scale_ticks = [0, 50, 100]

        self.ax_map.set_xlim(0, xlim)
        self.ax_map.set_ylim(0, ylim)

        # Draw scale bar (bottom-left corner)
        scale_x, scale_y = 10, 12
        self.ax_map.plot(
            [scale_x, scale_x + scale_length], [scale_y, scale_y],
            color=COLORS["header"], linewidth=3, solid_capstyle="butt"
        )
        for tick in scale_ticks:
            self.ax_map.plot(
                [scale_x + tick, scale_x + tick], [scale_y - 2, scale_y + 2],
                color=COLORS["header"], linewidth=2
            )
            self.ax_map.text(
                scale_x + tick, scale_y + 5, f"{tick}",
                fontsize=7, ha="center", color=COLORS["header"]
            )
        self.ax_map.text(
            scale_x + scale_length / 2, scale_y - 8,
            "meters",
            fontsize=8, ha="center", color=COLORS["header"], style="italic"
        )

        gws = [n for n in self.nodes_data if n["type"] == "Gateway"]
        for gw in gws:
            self.ax_map.scatter(
                gw["x"], gw["y"], c=COLORS["accent"], marker="^", s=200, zorder=5
            )
            # Dynamic Circle based on active protocol
            proto = _norm_proto(gw.get("protocol", "zigbee"))
            radius = PROTOCOL_RANGES.get(proto, 30)
            self.ax_map.add_patch(
                matplotlib.patches.Circle(
                    (gw["x"], gw["y"]), radius, color=COLORS["accent"], alpha=0.08,
                    linestyle="--", linewidth=0.5, fill=True
                )
            )

        # Draw range circles for all non-gateway nodes (very light)
        others = [n for n in self.nodes_data if n["type"] != "Gateway"]
        for n in others:
            proto = _norm_proto(n.get("protocol", "zigbee"))
            radius = PROTOCOL_RANGES.get(proto, 30)
            # Color based on state - green for active, red for disconnected
            if n["state"] == "active":
                circle_color = COLORS["success"]
            else:
                circle_color = COLORS["danger"]

            self.ax_map.add_patch(
                matplotlib.patches.Circle(
                    (n["x"], n["y"]), radius,
                    color=circle_color, alpha=0.05,
                    linestyle=":", linewidth=0.5, fill=True, zorder=1
                )
            )

        # Visual Blips
        active_ids = self.metrics.get_active_publishers(self.sim_env.now, window=0.5)
        pos_map = {n["id"]: (n["x"], n["y"]) for n in self.nodes_data}
        if gws:
            gw_pos = (gws[0]["x"], gws[0]["y"])
            for nid in active_ids:
                if nid in pos_map and nid not in [g["id"] for g in gws]:
                    start = pos_map[nid]
                    self.ax_map.plot(
                        [start[0], gw_pos[0]],
                        [start[1], gw_pos[1]],
                        color="#f1c40f",
                        linestyle="--",
                        linewidth=1.5,
                        alpha=0.7,
                        zorder=2,
                    )

                    # ---------------------------------------------------------------
                    # ZIGBEE MESH VISUALIZATION (node-to-node communication lines)
                    # ---------------------------------------------------------------
                    def _norm_proto(p):
                        return str(p).lower().replace("-", "").replace("_", "")

                    # Only show mesh if the protocol is Zigbee
                    active_proto = _norm_proto(self.protocol_var.get())
                    if active_proto == "zigbee":

                        # Zigbee range (from config)
                        zigbee_range = self.protocol_ranges.get("zigbee", 30)

                        # Build a map of node objects that are NOT gateways
                        node_by_id = {n["id"]: n for n in self.nodes_data if n["type"] != "Gateway"}

                        # Active nodes recently published
                        active_node_ids = [nid for nid in active_ids if nid in node_by_id]

                        # Draw purple dotted lines between nodes that are within ZigBee range
                        for src_id in active_node_ids:
                            sx, sy = node_by_id[src_id]["x"], node_by_id[src_id]["y"]

                            for dst_id, dst in node_by_id.items():
                                if src_id == dst_id:
                                    continue

                                dx = dst["x"] - sx
                                dy = dst["y"] - sy
                                dist = (dx * dx + dy * dy) ** 0.5

                                if dist <= zigbee_range:
                                    self.ax_map.plot(
                                        [sx, dst["x"]],
                                        [sy, dst["y"]],
                                        linestyle=":",
                                        linewidth=1.0,
                                        color="#9b59b6",  # purple
                                        alpha=0.6,
                                        zorder=1,
                                    )

        # Draw node markers
        if others:
            colors = [
                COLORS["success"] if n["state"] == "active" else COLORS["danger"]
                for n in others
            ]
            for i, n in enumerate(others):
                if n["id"] == self.selected_node_id:
                    colors[i] = "#f1c40f"

            self.ax_map.scatter(
                [n["x"] for n in others],
                [n["y"] for n in others],
                c=colors,
                s=80,
                edgecolors="white",
                zorder=10,
            )
            for n in others:
                self.ax_map.text(
                    n["x"], n["y"] - 8, n["id"], fontsize=7, ha="center", va="top"
                )

        self.canvas_map.draw()

    # --- THIS WAS MISSING IN PREVIOUS RESPONSE ---
    def _draw_charts(self):
        self.ax_q.clear()
        self.ax_q.plot(self.history["queue"], color=COLORS["accent"], linewidth=2)
        self.ax_q.fill_between(
            range(len(self.history["queue"])),
            self.history["queue"],
            color=COLORS["accent"],
            alpha=0.1,
        )
        self.ax_q.axis("off")
        mx = max(self.history["queue"]) if self.history["queue"] else 0
        self.ax_q.text(0, 0, f"Max: {mx}", fontsize=8, transform=self.ax_q.transAxes)
        self.canvas_q.draw()

        self.ax_h.clear()
        rates = self.metrics.get_topic_rates(self.sim_env.now, window=3.0)
        if rates:
            self.ax_h.barh(
                list(rates.keys()), list(rates.values()), color=COLORS["success"]
            )
            self.ax_h.set_xlabel("Msgs / Sec")
        else:
            self.ax_h.text(0.5, 0.5, "No Activity", ha="center")
            self.ax_h.axis("off")
        self.canvas_h.draw()


if __name__ == "__main__":
    ModernIotApp().mainloop()

