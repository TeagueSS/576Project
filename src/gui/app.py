import tkinter as tk
from tkinter import ttk
import random
from ..sim.environment import SimulationEnvironment
from ..sim.metrics import MetricsCollector

# Import View Components
from .views.controls import TopBar
from .views.palette import NodePalette
from .views.map_view import InteractiveMapView
from .views.info_panel import InfoPanel
from .views.bottom_graphs import BottomAnalysisPanel


class IotSimulationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IoT Mesh Simulation - CS576")
        self.geometry("1400x900")
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.sim_env = SimulationEnvironment()
        self.metrics = MetricsCollector()
        self.is_running = False

        # --- State ---
        self.nodes = []
        self.walls = []  # List of ((x1,y1), (x2,y2)) tuples
        self.selected_node_id = None
        self.placement_mode = None
        self.broker_queue = [0] * 50
        self.topic_counts = {"temp": 0, "humid": 0}

        self._init_layout()
        self._load_mock_scenario()
        self.after(100, self._update_loop)

    def _init_layout(self):
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.top_bar = TopBar(self, self.run_sim, self.pause_sim, self.set_speed)
        self.top_bar.grid(row=0, column=0, sticky="ew")

        self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=6, bg="#d9d9d9")
        self.main_pane.grid(row=1, column=0, sticky="nsew")

        self.palette = NodePalette(self.main_pane, self.on_palette_click)
        self.main_pane.add(self.palette, minsize=220, width=250)

        self.center_frame = tk.Frame(self.main_pane)
        self.main_pane.add(self.center_frame, minsize=600, width=900)

        self.center_pane = tk.PanedWindow(self.center_frame, orient=tk.VERTICAL, sashwidth=6, bg="#d9d9d9")
        self.center_pane.pack(fill=tk.BOTH, expand=True)

        self.map_container = tk.Frame(self.center_pane)
        self.center_pane.add(self.map_container, minsize=400, height=550)
        self._init_map_toolbar()

        # Pass handlers including the new on_wall_drawn
        self.map_view = InteractiveMapView(self.map_container,
                                           on_node_click=self.on_map_node_click,
                                           on_bg_click=self.on_map_bg_click,
                                           on_node_move=self.on_node_moved_on_map,
                                           on_wall_drawn=self.on_wall_drawn)
        self.map_view.pack(fill=tk.BOTH, expand=True)

        self.bottom_graphs = BottomAnalysisPanel(self.center_pane)
        self.center_pane.add(self.bottom_graphs, minsize=200, height=250)

        self.info_panel = InfoPanel(self.main_pane, self.update_node_settings)
        self.main_pane.add(self.info_panel, minsize=250, width=300)

    def _init_map_toolbar(self):
        toolbar = ttk.Frame(self.map_container)
        toolbar.pack(fill=tk.X, pady=2, padx=5)
        ttk.Label(toolbar, text="Tools:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))

        # Mode Switchers
        ttk.Button(toolbar, text="🗺 Normal Map", command=lambda: self.set_map_mode("map")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏️ Draw Walls", command=lambda: self.set_map_mode("draw_wall")).pack(side=tk.LEFT,
                                                                                                       padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=2)

        ttk.Button(toolbar, text="📋 Table", command=lambda: self.set_map_mode("table")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📈 Queue", command=lambda: self.set_map_mode("queue")).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📊 Heatmap", command=lambda: self.set_map_mode("heatmap")).pack(side=tk.LEFT, padx=2)

    def set_map_mode(self, mode):
        self.map_view.set_mode(mode)
        if mode == "draw_wall":
            self.info_panel.show_general_info(
                "WALL DRAWING MODE\n\nClick and drag on the map to build obstacles.\nObstacles block signals.")
        elif mode == "map":
            self.info_panel.show_general_info(
                "Map Mode\n\nSelect a node (Gateway/Sensor) to see its signal coverage heatmap.")

    # --- Interactions ---

    def on_palette_click(self, node_type):
        self.placement_mode = node_type
        self.set_map_mode("map")  # Ensure we are on the map
        self.info_panel.show_general_info(f"PLACEMENT MODE\n\nClick map to place {node_type}.")

    def on_map_bg_click(self, x, y):
        if self.placement_mode:
            new_id = f"n{len(self.nodes) + 1}"
            new_node = {
                "id": new_id, "x": x, "y": y,
                "type": self.placement_mode, "state": "active",
                "ip": f"192.168.1.{len(self.nodes) + 10}",
                "strength": 20.0, "battery": 100
            }
            self.nodes.append(new_node)
            self.placement_mode = None
            self._refresh_view()
            self.info_panel.show_node_details(new_node)
            self.selected_node_id = new_id
        else:
            self.selected_node_id = None
            self._refresh_view()
            self.info_panel.show_general_info("Ready.")

    def on_map_node_click(self, node_id):
        self.selected_node_id = node_id
        node = next((n for n in self.nodes if n['id'] == node_id), None)
        if node:
            self.info_panel.show_node_details(node)
        self._refresh_view()

    def on_node_moved_on_map(self, node_id, new_x, new_y):
        for n in self.nodes:
            if n['id'] == node_id:
                n['x'] = new_x
                n['y'] = new_y
                if self.selected_node_id == node_id:
                    self.info_panel.show_node_details(n)
                break
        self._refresh_view()

    def on_wall_drawn(self, start_pos, end_pos):
        self.walls.append((start_pos, end_pos))
        self._refresh_view()

    def update_node_settings(self, node_id, new_settings):
        for n in self.nodes:
            if n['id'] == node_id:
                n.update(new_settings)
        self._refresh_view()

    def _refresh_view(self):
        self.map_view.update_state(self.nodes, self.walls, self.selected_node_id, self.broker_queue, self.topic_counts)

    # --- Sim Control ---
    def run_sim(self):
        self.is_running = True
        self.info_panel.show_logs(["Sim Running..."])

    def pause_sim(self):
        self.is_running = False
        self.info_panel.show_logs(["Sim Paused."])

    def set_speed(self, val):
        print(f"Speed: {val}")

    def _update_loop(self):
        if self.is_running:
            self.bottom_graphs.update_data(
                random.randint(20, 60),
                random.randint(5, 15),
                random.randint(80, 100)
            )

            q = self.broker_queue[-1] + random.randint(-5, 5)
            self.broker_queue.append(max(0, min(100, q)))
            self.broker_queue.pop(0)

            # Update Topics
            self.topic_counts["temp"] += random.randint(0, 2)
            self.topic_counts["humid"] += random.randint(0, 1)

            # Random Walk
            for n in self.nodes:
                if n['type'] in ['iPhone', 'Laptop']:
                    n['x'] += random.uniform(-0.5, 0.5)
                    n['y'] += random.uniform(-0.5, 0.5)

            self._refresh_view()

        self.after(100, self._update_loop)

    def _load_mock_scenario(self):
        self.nodes = [
            {"id": "gw1", "x": 100, "y": 100, "type": "Gateway", "state": "active", "ip": "192.168.1.1",
             "strength": 20.0, "battery": 100},
            {"id": "s1", "x": 50, "y": 50, "type": "Sensor", "state": "active", "ip": "192.168.1.101", "strength": 15.0,
             "battery": 85},
            {"id": "m1", "x": 140, "y": 140, "type": "iPhone", "state": "active", "ip": "192.168.1.102",
             "strength": 10.0, "battery": 45},
        ]
        # Build a simple box room
        self.walls = [
            ((70, 20), (70, 180)),  # Vertical Left
            ((130, 20), (130, 180)),  # Vertical Right
            ((70, 180), (130, 180)),  # Bottom
            ((70, 20), (100, 20)),  # Top Part 1
            ((130, 20), (110, 20)),  # Top Part 2 (Leaving a door gap)
        ]
        self._refresh_view()