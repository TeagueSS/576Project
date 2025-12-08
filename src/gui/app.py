import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from ..sim.environment import SimulationEnvironment
from ..sim.metrics import MetricsCollector
from ..loader import ScenarioLoader

from .views.map_view import InteractiveMapView
from .views.info_panel import InfoPanel
from .views.stats_panel import StatsPanel
from .views.palette import NodePalette
from .views.queue_sparkline import QueueSparkline
from .views.topic_heatmap import TopicHeatmap
from .views.node_table import NodeTable

COLORS = {"bg": "#E3E9EE", "panel_bg": "#FFFFFF", "header_bg": "#2C3E50", "text_primary": "#2C3E50",
          "primary": "#3498DB", "danger": "#E74C3C"}


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class ModernIotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IoT Mesh Network Simulator - CS576")
        self.geometry("1400x950")
        self.configure(bg=COLORS["bg"])
        self._configure_styles()
        self.sim_env = None
        self.metrics = None
        self.loader = None
        self.is_running = False
        self.sim_speed = tk.DoubleVar(value=1.0)
        self.current_tool = "Select"
        self.history = {"queue": [0] * 50}
        self._build_layout()
        self.reset_simulation()
        self.after(100, self.update_loop)

    def _configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background=COLORS["bg"], foreground=COLORS["text_primary"], font=("Segoe UI", 10))
        self.style.configure("Card.TFrame", background=COLORS["panel_bg"], relief="flat")
        self.style.configure("Card.TLabel", background=COLORS["panel_bg"], foreground=COLORS["text_primary"])
        self.style.configure("CardHeader.TLabel", background=COLORS["panel_bg"], foreground=COLORS["text_primary"],
                             font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", padding=6, font=("Segoe UI", 9, "bold"))
        self.style.configure("Accent.TButton", background=COLORS["primary"], foreground="white")
        self.style.configure("Danger.TButton", background=COLORS["danger"], foreground="white")
        self.style.configure("Toolbar.TFrame", background="#FFFFFF")

    def _build_layout(self):
        toolbar = ttk.Frame(self, style="Toolbar.TFrame", padding=15)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(toolbar, text="CONTROLS:", background="#FFFFFF", font=("Segoe UI", 9, "bold"),
                  foreground="#7f8c8d").pack(side=tk.LEFT, padx=(5, 10))
        self.btn_run = ttk.Button(toolbar, text="▶ START", style="Accent.TButton", command=self.toggle_run)
        self.btn_run.pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="↻ RESET", command=self.reset_simulation).pack(side=tk.LEFT, padx=5)
        spd_frame = ttk.Frame(toolbar, style="Card.TFrame")
        spd_frame.pack(side=tk.LEFT, padx=30)
        ttk.Label(spd_frame, text="Speed:", style="Card.TLabel").pack(side=tk.LEFT, padx=5)
        ttk.Scale(spd_frame, from_=0.1, to=10.0, variable=self.sim_speed, orient=tk.HORIZONTAL, length=150).pack(
            side=tk.LEFT)
        ttk.Button(toolbar, text="☠️ FAILOVER", style="Danger.TButton", command=self.trigger_failover).pack(
            side=tk.RIGHT, padx=10)

        main_container = ttk.Frame(self, padding=15)
        main_container.pack(fill=tk.BOTH, expand=True)
        main_pane = tk.PanedWindow(main_container, orient=tk.HORIZONTAL, bg=COLORS["bg"], sashwidth=8,
                                   sashrelief="flat")
        main_pane.pack(fill=tk.BOTH, expand=True)

        map_card = ttk.Frame(main_pane, style="Card.TFrame")
        main_pane.add(map_card, minsize=600, width=900)
        map_header = ttk.Frame(map_card, style="Card.TFrame", padding=(15, 10))
        map_header.pack(fill=tk.X)
        ttk.Label(map_header, text="Network Topology", style="CardHeader.TLabel").pack(side=tk.LEFT)
        self.map_view = InteractiveMapView(map_card, on_node_click=self.on_node_selected,
                                           on_bg_click=self.on_map_bg_click, on_node_move=self.on_node_dragged,
                                           on_wall_drawn=lambda s, e: None)
        self.map_view.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        sidebar_container = ttk.Frame(main_pane)
        main_pane.add(sidebar_container, minsize=380)
        scroll_wrapper = ScrollableFrame(sidebar_container)
        scroll_wrapper.pack(fill="both", expand=True)
        sidebar = scroll_wrapper.scrollable_frame

        self.stats_panel = StatsPanel(sidebar)
        self.stats_panel.pack(fill=tk.X, pady=(0, 15))

        self.node_table = NodeTable(sidebar)
        self.node_table.pack(fill=tk.X, pady=(0, 15))

        self.palette = NodePalette(sidebar, on_node_type_selected=self.on_tool_changed,
                                   on_simulation_type_changed=self.on_experiment_changed)
        self.palette.pack(fill=tk.X, pady=(0, 15))
        self.info_panel = InfoPanel(sidebar, on_save_settings=self.on_node_edited)
        self.info_panel.pack(fill=tk.X, pady=(0, 15))

        graph_frame = ttk.Frame(sidebar, style="Card.TFrame", padding=10)
        graph_frame.pack(fill=tk.X, pady=(0, 15))
        self.notebook = ttk.Notebook(graph_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        t1 = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(t1, text="Queue Depth")
        self.queue_view = QueueSparkline(t1)
        self.queue_view.pack(fill=tk.BOTH, expand=True, pady=10)
        t2 = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(t2, text="Topic Rates")
        self.heatmap_view = TopicHeatmap(t2)
        self.heatmap_view.pack(fill=tk.BOTH, expand=True, pady=10)

    def reset_simulation(self):
        self.is_running = False
        if hasattr(self, 'btn_run'): self.btn_run.config(text="▶ START")
        self.sim_env = SimulationEnvironment()
        self.metrics = MetricsCollector()
        self.loader = ScenarioLoader(self.sim_env.env, self.metrics)
        self.history = {"queue": [0] * 50}
        proto = "e3"
        if hasattr(self, 'palette') and self.palette.sim_type_var.get():
            proto = self.palette.sim_type_var.get()
        self.loader.load_experiment(proto)
        self.current_tool = "Select"
        self._refresh_gui_data()

    def toggle_run(self):
        self.is_running = not self.is_running
        self.btn_run.config(text="⏸ PAUSE" if self.is_running else "▶ RESUME")

    def trigger_failover(self):
        if self.loader.broker:
            self.sim_env.env.process(self.loader.broker.failover_sequence(10.0))

    def update_loop(self):
        if self.is_running and self.sim_env:
            try:
                step = 0.2 * self.sim_speed.get()
                self.sim_env.run(until=self.sim_env.now + step)
                self._refresh_gui_data()
            except Exception as e:
                print(f"Sim Error: {e}")
                self.is_running = False
        self.after(50, self.update_loop)

    def _refresh_gui_data(self):
        nodes = self.loader.get_gui_node_data()
        for n_data in nodes:
            real_node = self.loader.get_node(n_data['id'])
            if real_node and hasattr(real_node, 'radio'):
                n_data['range'] = real_node.radio.config.get('range_m', 50)
        current_sel = self.info_panel.current_node['id'] if self.info_panel.current_node else None
        self.map_view.update_state(nodes, [], current_sel, [], {})
        self.stats_panel.update_metrics(self.metrics)

        if hasattr(self, 'node_table'):
            self.node_table.update_table(nodes)

        # --- FIX: Track BOTH Broker Queue AND Client Outgoing Queues ---
        broker_q = sum([len(q) for q in self.loader.broker.client_queues.values()])

        client_q = 0
        if self.loader.nodes:
            for n in self.loader.nodes:
                if hasattr(n, "mqtt") and hasattr(n.mqtt, "msg_queue"):
                    client_q += len(n.mqtt.msg_queue)

        total_backlog = broker_q + client_q
        # ---------------------------------------------------------------

        self.history["queue"].append(total_backlog)
        if len(self.history["queue"]) > 50: self.history["queue"].pop(0)
        self.queue_view.update_plot(self.history["queue"])
        rates = self.metrics.get_topic_rates(self.sim_env.now, window=3.0)
        self.heatmap_view.update_plot(rates)

    def on_tool_changed(self, tool_name):
        self.current_tool = tool_name

    def on_experiment_changed(self, exp_name):
        self.reset_simulation()

    def on_node_selected(self, node_id):
        nodes = self.loader.get_gui_node_data()
        node_data = next((n for n in nodes if n['id'] == node_id), None)
        if node_data:
            real_node = self.loader.get_node(node_id)
            if real_node:
                node_data['range'] = real_node.radio.config.get('range_m', 50)
            self.info_panel.show_node_details(node_data)
            self.map_view.selected_node_id = node_id
            self.map_view._draw_map()

    def on_map_bg_click(self, x, y):
        if self.current_tool == "Select":
            self.info_panel.show_general_info("Click a node to edit.")
            self.map_view.selected_node_id = None
            self.map_view._draw_map()
        else:
            self.loader.add_dynamic_node(self.current_tool, x, y)
            self.current_tool = "Select"
            self._refresh_gui_data()

    def on_node_dragged(self, node_id, new_x, new_y):
        node = self.loader.get_node(node_id)
        if node:
            node.x = new_x
            node.y = new_y
            if "Gateway" in node_id or isinstance(node, self.loader.get_node("Gateway").__class__):
                self.loader.gw_pos = (new_x, new_y)

    def on_node_edited(self, node_id, changes):
        node = self.loader.get_node(node_id)
        if not node: return
        if 'range' in changes and hasattr(node, 'radio'):
            node.radio.config['range_m'] = float(changes['range'])
        if 'state' in changes:
            if changes['state'] == 'dead':
                node.stop()
            elif changes['state'] == 'disconnected':
                node.toggle_connection()
        self._refresh_gui_data()


if __name__ == "__main__":
    ModernIotApp().mainloop()