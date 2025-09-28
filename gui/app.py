"""Tkinter GUI for IoT MQTT simulation."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from sim.experiments import ExperimentRunner
from sim.metrics import MetricSnapshot
from sim.config import SimulationConfig
from sim.utils.stats import compute_summary_stats, ExperimentSummary

# GUI Styling Constants
class Style:
    BG_COLOR = "#f0f0f0"
    ACCENT_COLOR = "#2E86AB"
    SUCCESS_COLOR = "#1B998B"
    WARNING_COLOR = "#F18F01"
    ERROR_COLOR = "#C73E1D"
    TEXT_COLOR = "#333333"
    
    FONT_SMALL = ("Segoe UI", 8)
    FONT_NORMAL = ("Segoe UI", 9)
    FONT_BOLD = ("Segoe UI", 9, "bold")
    FONT_LARGE = ("Segoe UI", 11, "bold")
    FONT_TITLE = ("Segoe UI", 12, "bold")
    
    PADDING_SMALL = 2
    PADDING_NORMAL = 5
    PADDING_LARGE = 10


@dataclass
class ClientState:
    client_id: str
    state: str
    phy: str
    topic: str
    energy_mj: float


class IoTMQTTApp:
    def __init__(self, root: tk.Tk, config_factory) -> None:
        """Initialize widgets and shared state for the GUI."""
        self.root = root
        self.root.title("IoT MQTT Simulation")
        self.config_factory = config_factory
        self.running = False
        self.snapshots: List[MetricSnapshot] = []
        self.topic_counts: Dict[str, deque] = {}
        self.queue_history = deque(maxlen=50)
        self.client_states: Dict[str, ClientState] = {}
        self.snapshot_index = 0
        self.client_meta: Dict[str, Dict[str, str]] = {}
        self.topic_palette: Dict[str, str] = {}
        self.area_size: Tuple[int, int] = (100, 100)
        self.node_count_var = tk.IntVar(value=10)
        self.node_count_label = tk.StringVar(value="Nodes: 10")
        self.current_run: Dict[str, object] | None = None
        self.current_composite: Dict[str, object] | None = None
        self.composite_results: Dict[str, List[ExperimentSummary]] = {}
        self.stop_requested = False
        self.current_runner = None
        self.current_network = None
        self.experiment_notes = {
            "baseline": "Baseline mix of BLE/Zigbee sensors with one mobile Wi-Fi client.",
            "duty_cycle": "E1 Duty Cycle – Zigbee nodes restricted to 5% duty cycle; compare latency/energy.",
            "protocol_compare": "E2 Protocol Compare – round-robin BLE/Wi-Fi/Zigbee assignments to study trade-offs.",
            "topology_failover": "E3 Topology Failover – broker outage plus moving gateway tests reconnect behavior.",
            "ble_only": "All nodes use BLE PHY for low-power operation comparison.",
            "wifi_only": "All nodes use Wi-Fi PHY for high-throughput operation comparison.",
            "zigbee_only": "All nodes use Zigbee PHY for ultra-low-power mesh operation comparison.",
        }
        self.composite_experiment_notes = {
            "E1": "Duty Cycle Impact Study: Compares baseline vs low duty cycle (5%) Zigbee operation to analyze sleep ratio effects on latency and battery life.",
            "E2": "Protocol Comparison Study: Evaluates BLE, Wi-Fi, and Zigbee protocols across delivery ratio, latency, and energy consumption metrics.",
            "E3": "Topology & Broker Failure Study: Tests system resilience during broker outages and gateway mobility, measuring recovery time and message loss."
        }
        self._build_ui()

    def _set_controls_enabled(self, running: bool) -> None:
        """Unified control state management to avoid OS-specific widget disable bugs."""
        if running:
            # Start disabled, Stop/Failover enabled
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.failover_button.configure(state=tk.NORMAL)
            try:
                self.stop_button.state(['!disabled'])
                self.failover_button.state(['!disabled'])
            except Exception:
                pass
        else:
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)
            self.failover_button.configure(state=tk.DISABLED)
            try:
                self.start_button.state(['!disabled'])
                self.stop_button.state(['disabled'])
                self.failover_button.state(['disabled'])
            except Exception:
                pass

    def _build_ui(self) -> None:
        """Construct layout panes, tabs, and controls with enhanced styling."""
        # Configure root window
        self.root.configure(bg=Style.BG_COLOR)
        
        # Configure ttk styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=Style.FONT_TITLE, foreground=Style.ACCENT_COLOR)
        style.configure('Heading.TLabel', font=Style.FONT_LARGE, foreground=Style.TEXT_COLOR)
        style.configure('Accent.TButton', background=Style.ACCENT_COLOR, foreground='white')
        
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=Style.PADDING_NORMAL, pady=Style.PADDING_NORMAL)

        left_frame = ttk.Frame(main_pane, padding=Style.PADDING_NORMAL)
        right_frame = ttk.Frame(main_pane, padding=Style.PADDING_NORMAL)
        main_pane.add(left_frame, weight=3)
        main_pane.add(right_frame, weight=2)

        # Enhanced map canvas with better styling
        map_frame = ttk.LabelFrame(left_frame, text="🗺️ Geographic Network Map", style='Heading.TLabelframe')
        map_frame.pack(fill=tk.BOTH, expand=True, pady=(0, Style.PADDING_NORMAL))
        self.map_canvas = tk.Canvas(
            map_frame, 
            width=500, height=450, 
            background="white", 
            relief=tk.SUNKEN, 
            borderwidth=2,
            highlightthickness=1,
            highlightcolor=Style.ACCENT_COLOR
        )
        self.map_canvas.pack(fill=tk.BOTH, expand=True, padx=Style.PADDING_SMALL, pady=Style.PADDING_SMALL)

        # Enhanced topic heatmap
        heatmap_frame = ttk.LabelFrame(left_frame, text="📊 Topic Activity (msg/sec)", style='Heading.TLabelframe')
        heatmap_frame.pack(fill=tk.X)
        
        # Add scrollbar to heatmap
        heatmap_container = ttk.Frame(heatmap_frame)
        heatmap_container.pack(fill=tk.X, padx=Style.PADDING_SMALL, pady=Style.PADDING_SMALL)
        
        self.heatmap_list = tk.Listbox(
            heatmap_container, 
            height=4, 
            font=Style.FONT_NORMAL,
            selectmode=tk.SINGLE,
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=1,
            highlightcolor=Style.ACCENT_COLOR
        )
        heatmap_scrollbar = ttk.Scrollbar(heatmap_container, orient=tk.VERTICAL, command=self.heatmap_list.yview)
        self.heatmap_list.configure(yscrollcommand=heatmap_scrollbar.set)
        
        self.heatmap_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        heatmap_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enhanced Controls section (robust, platform-friendly)
        control_frame = ttk.LabelFrame(right_frame, text="🎮 Simulation Controls", style='Heading.TLabelframe')
        control_frame.pack(fill=tk.X, pady=(0, Style.PADDING_NORMAL))
        try:
            control_frame.lift()
        except Exception:
            pass

        # Row 1: Run / Stop
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, padx=Style.PADDING_NORMAL, pady=Style.PADDING_SMALL)
        self.start_button = ttk.Button(row1, text="▶️ Run", command=self.start_simulation, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=Style.PADDING_SMALL)
        self.stop_button = ttk.Button(row1, text="⏹️ Stop", command=self.stop_simulation)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=Style.PADDING_SMALL)

        # Row 2: Failover (explicit, calls network API)
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, padx=Style.PADDING_NORMAL, pady=Style.PADDING_SMALL)
        self.failover_button = ttk.Button(row2, text="⚠️ Trigger Failover", command=self._ui_trigger_failover)
        self.failover_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=Style.PADDING_SMALL)

        # Node count slider with better styling
        slider_frame = ttk.LabelFrame(control_frame, text="Network Size")
        slider_frame.pack(fill=tk.X, padx=Style.PADDING_NORMAL, pady=Style.PADDING_SMALL)
        
        slider_container = ttk.Frame(slider_frame)
        slider_container.pack(fill=tk.X, padx=Style.PADDING_SMALL, pady=Style.PADDING_SMALL)
        
        ttk.Label(slider_container, text="Node Count:", font=Style.FONT_NORMAL).pack(side=tk.LEFT)
        ttk.Label(slider_container, textvariable=self.node_count_label, font=Style.FONT_BOLD).pack(side=tk.RIGHT)
        
        self.node_slider = tk.Scale(
            slider_container,
            from_=6, to=40,
            orient=tk.HORIZONTAL,
            resolution=1,
            variable=self.node_count_var,
            command=self._handle_node_slider,
            font=Style.FONT_SMALL,
            bg=Style.BG_COLOR,
            highlightthickness=0,
            troughcolor=Style.ACCENT_COLOR,
            activebackground=Style.SUCCESS_COLOR
        )
        self.node_slider.pack(fill=tk.X, pady=Style.PADDING_SMALL)

        # Ensure initial control states
        self._set_controls_enabled(running=False)

        # Enhanced Tabs with icons and better organization
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=Style.PADDING_NORMAL)

        # Create tabs with icons and padding
        overview_tab = ttk.Frame(notebook, padding=Style.PADDING_NORMAL)
        clients_tab = ttk.Frame(notebook, padding=Style.PADDING_NORMAL)
        composite_tab = ttk.Frame(notebook, padding=Style.PADDING_NORMAL)
        results_tab = ttk.Frame(notebook, padding=Style.PADDING_NORMAL)
        
        notebook.add(overview_tab, text="📊 Overview")
        notebook.add(clients_tab, text="🔗 Clients")
        notebook.add(composite_tab, text="🔬 Studies")
        notebook.add(results_tab, text="📈 Results")

        # Enhanced broker queue visualization
        broker_frame = ttk.LabelFrame(overview_tab, text="📈 Broker Queue Activity", style='Heading.TLabelframe')
        broker_frame.pack(fill=tk.X, pady=(0, Style.PADDING_NORMAL))
        self.queue_canvas = tk.Canvas(
            broker_frame, 
            height=70, 
            background="#1e1e1e",
            relief=tk.SUNKEN,
            borderwidth=1,
            highlightthickness=1,
            highlightcolor=Style.ACCENT_COLOR
        )
        self.queue_canvas.pack(fill=tk.X, padx=Style.PADDING_SMALL, pady=Style.PADDING_SMALL)

        # Enhanced statistics panel with grid layout
        panel_frame = ttk.LabelFrame(overview_tab, text="📊 Real-time Metrics", style='Heading.TLabelframe')
        panel_frame.pack(fill=tk.X, pady=(0, Style.PADDING_NORMAL))
        
        stats_container = ttk.Frame(panel_frame)
        stats_container.pack(fill=tk.X, padx=Style.PADDING_NORMAL, pady=Style.PADDING_SMALL)
        
        # Create metric variables with better formatting
        self.delivery_var = tk.StringVar(value="📤 Delivery: 0%")
        self.latency_var = tk.StringVar(value="⏱️ Latency: 0 ms")
        self.dup_var = tk.StringVar(value="🔄 Duplicates: 0")
        self.energy_var = tk.StringVar(value="⚡ Energy: 0 mJ")
        self.sleep_ratio_var = tk.StringVar(value="🛌 Sleep Ratio: 0.00")
        self.queue_drops_var = tk.StringVar(value="🧺 Queue Drops: 0")
        
        # Arrange metrics in a 2x2 grid
        metrics = [
            (self.delivery_var, Style.SUCCESS_COLOR),
            (self.latency_var, Style.WARNING_COLOR),
            (self.dup_var, Style.ERROR_COLOR),
            (self.energy_var, Style.ACCENT_COLOR)
        ]
        
        for i, (var, color) in enumerate(metrics):
            row, col = i // 2, i % 2
            metric_frame = ttk.Frame(stats_container, relief=tk.RIDGE, borderwidth=1)
            metric_frame.grid(row=row, column=col, padx=Style.PADDING_SMALL, pady=Style.PADDING_SMALL, sticky="ew")
            
            label = ttk.Label(metric_frame, textvariable=var, font=Style.FONT_NORMAL, foreground=color)
            label.pack(padx=Style.PADDING_NORMAL, pady=Style.PADDING_SMALL)
        
        # Configure grid weights
        for i in range(2):
            stats_container.grid_columnconfigure(i, weight=1)

        # Secondary line of metrics
        metrics2 = [
            (self.sleep_ratio_var, Style.SUCCESS_COLOR),
            (self.queue_drops_var, Style.ERROR_COLOR),
        ]
        second_row = ttk.Frame(panel_frame)
        second_row.pack(fill=tk.X, padx=Style.PADDING_NORMAL, pady=Style.PADDING_SMALL)
        for i, (var, color) in enumerate(metrics2):
            metric_frame = ttk.Frame(second_row, relief=tk.RIDGE, borderwidth=1)
            metric_frame.grid(row=0, column=i, padx=Style.PADDING_SMALL, pady=Style.PADDING_SMALL, sticky="ew")
            label = ttk.Label(metric_frame, textvariable=var, font=Style.FONT_NORMAL, foreground=color)
            label.pack(padx=Style.PADDING_NORMAL, pady=Style.PADDING_SMALL)
            second_row.grid_columnconfigure(i, weight=1)

        # Enhanced battery panel
        energy_frame = ttk.LabelFrame(overview_tab, text="🔋 Battery Life Estimates", style='Heading.TLabelframe')
        energy_frame.pack(fill=tk.BOTH, expand=True, pady=(0, Style.PADDING_NORMAL))
        
        battery_container = ttk.Frame(energy_frame)
        battery_container.pack(fill=tk.BOTH, expand=True, padx=Style.PADDING_SMALL, pady=Style.PADDING_SMALL)
        
        self.battery_list = tk.Listbox(
            battery_container, 
            height=4, 
            font=Style.FONT_NORMAL,
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=1,
            highlightcolor=Style.ACCENT_COLOR,
            selectmode=tk.SINGLE
        )
        battery_scrollbar = ttk.Scrollbar(battery_container, orient=tk.VERTICAL, command=self.battery_list.yview)
        self.battery_list.configure(yscrollcommand=battery_scrollbar.set)
        
        self.battery_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        battery_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Export button with better styling
        export_frame = ttk.Frame(energy_frame)
        export_frame.pack(fill=tk.X, padx=Style.PADDING_SMALL, pady=(0, Style.PADDING_SMALL))
        ttk.Button(
            export_frame, text="💾 Export CSV", command=self.export_data,
            style='Accent.TButton'
        ).pack(fill=tk.X)

        # Client state tab
        columns = ("id", "state", "phy", "topic", "energy")
        headers = ("Client", "State", "PHY", "Topic", "Energy (mJ)")
        self.client_tree = ttk.Treeview(clients_tab, columns=columns, show="headings")
        for col, label in zip(columns, headers):
            self.client_tree.heading(col, text=label)
            self.client_tree.column(col, width=130 if col != "topic" else 200, anchor=tk.W)
        self.client_tree.pack(fill=tk.BOTH, expand=True)


        # Results tab widgets
        self.results_queue = []
        results_top = ttk.Frame(results_tab)
        results_top.pack(fill=tk.X, pady=4)
        ttk.Button(results_top, text="Run Selected", command=self.run_selected_result).pack(side=tk.LEFT, padx=2)
        ttk.Button(results_top, text="Clear Results", command=self.clear_results).pack(side=tk.LEFT, padx=2)
        self.results_tree = ttk.Treeview(
            results_tab,
            columns=("scenario", "delivery", "latency", "duplicates", "energy"),
            show="headings",
        )
        headings = {
            "scenario": "Scenario",
            "delivery": "Delivery %",
            "latency": "Avg Latency (ms)",
            "duplicates": "Duplicates",
            "energy": "Energy (mJ)",
        }
        for col, title in headings.items():
            self.results_tree.heading(col, text=title)
            self.results_tree.column(col, width=130, anchor=tk.W)
        self.results_tree.pack(fill=tk.BOTH, expand=True)

        # Composite Experiments tab
        composite_top = ttk.Frame(composite_tab)
        composite_top.pack(fill=tk.X, pady=4)
        ttk.Label(composite_top, text="Composite Experiments", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        # E1 - Duty Cycle Study
        e1_frame = ttk.LabelFrame(composite_tab, text="E1: Duty Cycle Impact Study")
        e1_frame.pack(fill=tk.X, pady=5)
        ttk.Button(e1_frame, text="Run E1 Study", command=self.run_e1_experiment).pack(side=tk.LEFT, padx=4)
        ttk.Label(e1_frame, text="Compares baseline vs 5% duty cycle Zigbee").pack(side=tk.LEFT, padx=10)
        
        # E2 - Protocol Comparison
        e2_frame = ttk.LabelFrame(composite_tab, text="E2: Protocol Comparison Study")
        e2_frame.pack(fill=tk.X, pady=5)
        ttk.Button(e2_frame, text="Run E2 Study", command=self.run_e2_experiment).pack(side=tk.LEFT, padx=4)
        ttk.Label(e2_frame, text="Compares BLE vs Wi-Fi vs Zigbee protocols").pack(side=tk.LEFT, padx=10)
        
        # E3 - Topology & Failure Study
        e3_frame = ttk.LabelFrame(composite_tab, text="E3: Topology & Broker Failure Study")
        e3_frame.pack(fill=tk.X, pady=5)
        ttk.Button(e3_frame, text="Run E3 Study", command=self.run_e3_experiment).pack(side=tk.LEFT, padx=4)
        ttk.Label(e3_frame, text="Tests system resilience during failures").pack(side=tk.LEFT, padx=10)
        
        # Composite Results Display
        composite_results_frame = ttk.LabelFrame(composite_tab, text="Composite Results")
        composite_results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Results control buttons
        composite_controls = ttk.Frame(composite_results_frame)
        composite_controls.pack(fill=tk.X, pady=2)
        ttk.Button(composite_controls, text="Clear All Results", command=self.clear_composite_results).pack(side=tk.LEFT, padx=2)
        ttk.Button(composite_controls, text="Export Comparison", command=self.export_composite_results).pack(side=tk.LEFT, padx=2)
        
        # Scrollable frame for results
        canvas_frame = ttk.Frame(composite_results_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.composite_canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.composite_canvas.yview)
        self.composite_scrollable_frame = ttk.Frame(self.composite_canvas)
        
        self.composite_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.composite_canvas.configure(scrollregion=self.composite_canvas.bbox("all"))
        )
        
        self.composite_canvas.create_window((0, 0), window=self.composite_scrollable_frame, anchor="nw")
        self.composite_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.composite_canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill=tk.Y)

    def start_simulation(self) -> None:
        """Start a single simulation run."""
        if self.running:
            return
        # Since we removed the scenarios tab, start simulation directly with baseline
        scenario = "baseline"
        self.current_run = {"scenario": scenario}
        self._trigger_run()

    def _trigger_run(self) -> None:
        if self.running:
            return
        self.running = True
        self.snapshot_index = 0
        self.snapshots = []
        self.node_count_label.set(f"Nodes: {self.node_count_var.get()}")
        # Unified control state transition
        self._set_controls_enabled(running=True)
        self.stop_requested = False
        thread = threading.Thread(target=self._run_sim_thread, daemon=True)
        thread.start()

    def stop_simulation(self) -> None:
        """Signal background thread to wind down and reset controls."""
        self.stop_requested = True
        self.running = False
        self.current_runner = None
        self.current_network = None
        self._set_controls_enabled(running=False)

    def trigger_failover(self) -> None:
        """Manually trigger broker failover during simulation."""
        if not self.running or not self.current_network:
            messagebox.showwarning("Failover", "No simulation is currently running to trigger failover.")
            return
        
        try:
            # Trigger immediate broker failover
            for session in self.current_network.sessions.values():
                session.connected = False
                self.current_network.metrics.update_client_state(session.client_id, "reconnecting")
            
            messagebox.showinfo("Failover", "✅ Broker failover triggered! Clients will attempt to reconnect.")
            
            # Schedule broker recovery after 10 seconds
            self.root.after(10000, self._recover_broker)
            
        except Exception as e:
            messagebox.showerror("Failover Error", f"Failed to trigger failover: {str(e)}")

    def _ui_trigger_failover(self) -> None:
        """UI wrapper: use network's internal failover coroutine for accuracy."""
        if not self.running or not self.current_network:
            messagebox.showwarning("Failover", "No simulation is currently running to trigger failover.")
            return
        try:
            # Prefer network's native failover to keep SimPy timing correct
            if hasattr(self.current_network, "trigger_failover"):
                self.current_network.trigger_failover(down_seconds=10.0)
                messagebox.showinfo("Failover", "✅ Broker failover triggered! Clients will attempt to reconnect.")
            else:
                self.trigger_failover()
        except Exception as e:
            messagebox.showerror("Failover Error", f"Failed to trigger failover: {str(e)}")

    def _recover_broker(self) -> None:
        """Recover broker after failover."""
        if self.current_network:
            try:
                for session in self.current_network.sessions.values():
                    if not session.connected:
                        self.current_network.connect(session.client_id, session.clean_session, session.keep_alive)
            except Exception:
                pass  # Simulation might have ended

    def _handle_node_slider(self, _: str) -> None:
        """Update live label as slider moves."""
        self.node_count_label.set(f"Nodes: {self.node_count_var.get()}")

    def export_data(self) -> None:
        if not self.snapshots:
            messagebox.showwarning("No data", "Run a simulation first")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("timestamp,delivery_ratio,avg_latency_ms,duplicates,energy_mj,queue_depth\n")
            for snap in self.snapshots:
                fh.write(
                    f"{snap.timestamp},{snap.delivery_ratio:.3f},{snap.avg_latency_ms:.2f},{snap.duplicates},{snap.energy_consumed_mj:.3f},{snap.broker_queue_depth}\n"
                )
        messagebox.showinfo("Export", f"Saved to {path}")

    def _run_sim_thread(self) -> None:
        """Background worker running SimPy experiment to completion."""
        scenario = self.current_run["scenario"] if self.current_run else "baseline"
        config: SimulationConfig = self.config_factory(scenario, self.node_count_var.get())
        self.client_meta = {
            node.node_id: {"phy": node.phy.upper(), "topic": node.topic}
            for node in config.nodes
        }
        self.area_size = config.area_size
        palette = ["#2E86AB", "#F18F01", "#C73E1D", "#6F2DBD", "#1B998B", "#BFD200", "#FF6978"]
        topics = list(dict.fromkeys(config.topic_list or [node.topic for node in config.nodes]))
        self.topic_palette = {topic: palette[idx % len(palette)] for idx, topic in enumerate(topics)}
        runner = ExperimentRunner(config)
        self.current_runner = runner
        # Ensure failover/stop buttons remain clickable by never disabling the parent frame
        result = runner.run(
            scenario,
            stop_flag=lambda: self.stop_requested,
            on_network=lambda net: setattr(self, "current_network", net),
        )
        if self.stop_requested:
            self.snapshots = result.snapshots
            self.root.after(0, self._handle_stop_midrun)
        else:
            self.snapshots = result.snapshots
            self.root.after(0, self._update_gui_after_run)
        self.running = False

    def _update_gui_after_run(self) -> None:
        self.stop_simulation()
        if not self.snapshots:
            return
        if self.current_run:
            last = self.snapshots[-1]
            self.results_tree.insert(
                "",
                tk.END,
                values=(
                    self.current_run["scenario"],
                    f"{last.delivery_ratio*100:.1f}",
                    f"{last.avg_latency_ms:.1f}",
                    last.duplicates,
                    f"{last.energy_consumed_mj:.1f}",
                ),
            )
            self.current_run = None
        self.snapshot_index = 0
        self._playback_snapshots()

    def _handle_stop_midrun(self) -> None:
        """Cleanup when stop button fires mid-simulation."""
        self.stop_simulation()
        self.snapshots = []
        self.current_run = None

    def _playback_snapshots(self) -> None:
        """Animate metrics/time-series snapshots in the UI."""
        if not self.snapshots or self.snapshot_index >= len(self.snapshots):
            return
        snap = self.snapshots[self.snapshot_index]
        self._update_stats(snap)
        self._update_queue_sparkline(self.snapshot_index)
        self._update_topic_heatmap(snap)
        self._update_client_table(snap)
        self._draw_map(snap)
        self.snapshot_index += 1
        if self.snapshot_index < len(self.snapshots):
            self.root.after(500, self._playback_snapshots)

    def _update_stats(self, snapshot: MetricSnapshot) -> None:
        """Update statistics display with enhanced formatting."""
        # Format delivery ratio as percentage with color coding
        delivery_pct = snapshot.delivery_ratio * 100
        delivery_icon = "✅" if delivery_pct >= 95 else "⚠️" if delivery_pct >= 80 else "❌"
        self.delivery_var.set(f"{delivery_icon} Delivery: {delivery_pct:.1f}%")
        
        # Format latency with appropriate units
        if snapshot.avg_latency_ms < 100:
            latency_icon = "🟢"
        elif snapshot.avg_latency_ms < 500:
            latency_icon = "🟡"
        else:
            latency_icon = "🔴"
        self.latency_var.set(f"{latency_icon} Latency: {snapshot.avg_latency_ms:.1f} ms")
        
        # Format duplicates with warning if high
        dup_icon = "🔄" if snapshot.duplicates == 0 else "⚠️"
        self.dup_var.set(f"{dup_icon} Duplicates: {snapshot.duplicates}")
        
        # Format energy consumption
        energy_mj = snapshot.energy_consumed_mj
        if energy_mj < 1000:
            energy_str = f"{energy_mj:.1f} mJ"
        elif energy_mj < 1000000:
            energy_str = f"{energy_mj/1000:.1f} J"
        else:
            energy_str = f"{energy_mj/1000000:.1f} kJ"
        self.energy_var.set(f"⚡ Energy: {energy_str}")
        # New metrics: sleep ratio and queue drops
        self.sleep_ratio_var.set(f"🛌 Sleep Ratio: {snapshot.sleep_ratio_avg:.2f}")
        self.queue_drops_var.set(f"🧺 Queue Drops: {snapshot.queue_drops}")
        # Enhanced battery list display
        self.battery_list.delete(0, tk.END)
        if not snapshot.battery_estimate_days:
            self.battery_list.insert(tk.END, "🔋 No battery data available")
        else:
            # Sort by battery life for better visualization
            sorted_batteries = sorted(
                snapshot.battery_estimate_days.items(), 
                key=lambda x: x[1] if x[1] != float("inf") else 999999
            )
            for client_id, days in sorted_batteries:
                if days == float("inf"):
                    icon = "🟢"
                    label = "∞"
                elif days > 30:
                    icon = "🟢"
                    label = f"{days:.1f} d"
                elif days > 7:
                    icon = "🟡"
                    label = f"{days:.1f} d"
                else:
                    icon = "🔴"
                    label = f"{days:.1f} d"
                self.battery_list.insert(tk.END, f"{icon} {client_id}: {label}")

    def _update_queue_sparkline(self, end_index: int | None = None) -> None:
        """Enhanced queue depth visualization with better styling."""
        self.queue_canvas.delete("all")
        if not self.snapshots:
            # Show placeholder text
            w = self.queue_canvas.winfo_width()
            h = self.queue_canvas.winfo_height()
            self.queue_canvas.create_text(
                w//2, h//2, text="📊 Waiting for queue data...", 
                fill="#888", font=Style.FONT_NORMAL
            )
            return
            
        if end_index is None:
            relevant = self.snapshots
        else:
            start = max(0, end_index - 49)
            relevant = self.snapshots[start : end_index + 1]
            
        if len(relevant) < 2:
            return
            
        data = [snap.broker_queue_depth for snap in relevant]
        w = self.queue_canvas.winfo_width()
        h = self.queue_canvas.winfo_height()
        
        if w <= 1 or h <= 1:
            return
            
        # Draw grid lines for better readability
        grid_color = "#333"
        for i in range(1, 4):
            y = (h * i) // 4
            self.queue_canvas.create_line(0, y, w, y, fill=grid_color, dash=(2, 2))
        
        # Calculate points
        step = w / (len(data) - 1) if len(data) > 1 else w
        max_val = max(data) or 1
        points = []
        
        for idx, val in enumerate(data):
            x = idx * step
            y = h - (val / max_val) * (h - 10)  # Leave margin at top/bottom
            points.extend([x, y])
        
        # Draw the main line with gradient effect
        if len(points) >= 4:
            self.queue_canvas.create_line(points, fill=Style.SUCCESS_COLOR, width=3, smooth=True)
            
            # Add fill area under the curve
            fill_points = points.copy()
            fill_points.extend([points[-2], h, points[0], h])  # Close the shape
            self.queue_canvas.create_polygon(
                fill_points, fill=Style.SUCCESS_COLOR, outline="", stipple="gray50"
            )
        
        # Add current value indicator
        if data:
            current_val = data[-1]
            self.queue_canvas.create_text(
                w - 5, 10, text=f"Queue: {current_val}", 
                anchor=tk.NE, fill="white", font=Style.FONT_SMALL
            )
            
            # Add max value indicator
            max_val_text = f"Max: {max(data)}"
            self.queue_canvas.create_text(
                5, 10, text=max_val_text, 
                anchor=tk.NW, fill="#ccc", font=Style.FONT_SMALL
            )

    def _update_topic_heatmap(self, snapshot: MetricSnapshot) -> None:
        """Enhanced topic heatmap with better formatting and icons."""
        self.heatmap_list.delete(0, tk.END)
        if not snapshot.topic_rates:
            self.heatmap_list.insert(tk.END, "📊 No active topics")
            return
            
        # Sort topics by rate for better visualization
        sorted_topics = sorted(snapshot.topic_rates.items(), key=lambda x: x[1], reverse=True)
        
        for topic, rate in sorted_topics:
            # Add activity indicators based on rate
            if rate >= 1.0:
                icon = "🔥"  # High activity
            elif rate >= 0.1:
                icon = "📈"  # Medium activity
            else:
                icon = "📉"  # Low activity
                
            # Shorten topic names for better display
            display_topic = topic.split('/')[-1] if '/' in topic else topic
            rate_str = f"{rate:.2f}" if rate < 10 else f"{rate:.1f}"
            
            self.heatmap_list.insert(tk.END, f"{icon} {display_topic}: {rate_str} msg/s")

    def _update_client_table(self, snapshot: MetricSnapshot) -> None:
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)
        for client_id, state in snapshot.client_states.items():
            energy = snapshot.energy_per_client.get(client_id, 0.0)
            meta = self.client_meta.get(client_id, {})
            phy = meta.get("phy", "-")
            topic = meta.get("topic", "-")
            self.client_tree.insert("", tk.END, values=(client_id, state, phy, topic, f"{energy:.2f}"))

    def _draw_map(self, snapshot: MetricSnapshot) -> None:
        """Draw the geographic map with nodes, gateways, and enhanced legend."""
        self.map_canvas.delete("all")
        width = max(self.map_canvas.winfo_width(), 1)
        height = max(self.map_canvas.winfo_height(), 1)
        area_x, area_y = self.area_size

        # Draw grid background for better visualization
        self._draw_map_grid(width, height)
        
        # Draw gateway coverage areas
        gateways = getattr(snapshot, "gateways", {})
        for gw_id, gateway in gateways.items():
            self._draw_gateway(gateway, gw_id, width, height, area_x, area_y)

        # Draw client nodes and collect statistics
        phy_counts, connection_states = self._draw_clients(snapshot, width, height, area_x, area_y)
        
        # Draw enhanced legend
        self._draw_enhanced_legend(width, height, phy_counts, connection_states)

    def _draw_map_grid(self, width: int, height: int) -> None:
        """Draw a subtle grid background."""
        grid_color = "#f8f8f8"
        step = 50
        for i in range(0, width, step):
            self.map_canvas.create_line(i, 0, i, height, fill=grid_color, width=1)
        for i in range(0, height, step):
            self.map_canvas.create_line(0, i, width, i, fill=grid_color, width=1)

    def _draw_gateway(self, gateway: Dict, gw_id: str, width: int, height: int, area_x: int, area_y: int) -> None:
        """Draw a single gateway with its coverage area."""
        gx, gy = gateway["position"]
        radius = gateway.get("range", 30)
        cx = gx / area_x * width
        cy = gy / area_y * height
        r = radius / max(area_x, area_y) * min(width, height)
        
        # Gateway coverage circle
        self.map_canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r, 
            outline="#cccccc", fill="#f0f0f0", stipple="gray25", width=2, dash=(8, 4)
        )
        
        # Gateway icon
        self.map_canvas.create_oval(
            cx - 8, cy - 8, cx + 8, cy + 8, 
            fill=Style.ACCENT_COLOR, outline="white", width=2
        )
        self.map_canvas.create_text(
            cx, cy - 15, text=f"📡 {gw_id}", 
            font=Style.FONT_SMALL, fill=Style.TEXT_COLOR, anchor=tk.S
        )

    def _draw_clients(self, snapshot: MetricSnapshot, width: int, height: int, area_x: int, area_y: int) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Draw client nodes and return statistics."""
        phy_counts: Dict[str, int] = {}
        connection_states: Dict[str, int] = {"connected": 0, "disconnected": 0, "reconnecting": 0}
        
        for client_id, pos in snapshot.positions.items():
            x, y = pos
            topic = self.client_meta.get(client_id, {}).get("topic", "")
            phy = self.client_meta.get(client_id, {}).get("phy", "")
            state = snapshot.client_states.get(client_id, "unknown")
            
            phy_counts[phy] = phy_counts.get(phy, 0) + 1
            connection_states[state] = connection_states.get(state, 0) + 1
            
            cx = x / area_x * width
            cy = y / area_y * height
            
            # Node appearance based on PHY and state
            color = self.topic_palette.get(topic, "#1f77b4")
            size = {"BLE": 6, "ZIGBEE": 8, "WIFI": 10}.get(phy, 7)
            outline_color = {"connected": "green", "disconnected": "red", "reconnecting": "orange"}.get(state, "black")
            
            # Draw node
            self.map_canvas.create_oval(
                cx - size, cy - size, cx + size, cy + size, 
                fill=color, outline=outline_color, width=2
            )
            
            # Node label with improved positioning
            label_offset = size + 8
            self.map_canvas.create_text(
                cx + label_offset, cy, text=client_id, 
                anchor=tk.W, font=Style.FONT_SMALL, fill=Style.TEXT_COLOR
            )
            
            # PHY indicator
            phy_symbol = {"BLE": "B", "ZIGBEE": "Z", "WIFI": "W"}.get(phy, "?")
            self.map_canvas.create_text(
                cx, cy, text=phy_symbol, 
                font=("Arial", 6, "bold"), fill="white"
            )
        
        return phy_counts, connection_states

    def _draw_enhanced_legend(self, width: int, height: int, phy_counts: Dict[str, int], connection_states: Dict[str, int]) -> None:
        """Draw an enhanced, organized legend."""
        legend_width = 200
        legend_x = width - legend_width - 10
        legend_y = 10
        
        # Calculate legend height dynamically
        sections = 5  # Topics, PHY, Connection, Gateway, Status
        topic_lines = len(self.topic_palette)
        phy_lines = len(phy_counts)
        legend_height = 30 + (topic_lines * 20) + (phy_lines * 20) + (sections * 35)
        
        # Legend background with shadow effect
        self.map_canvas.create_rectangle(
            legend_x + 2, legend_y + 2, legend_x + legend_width + 2, legend_y + legend_height + 2,
            fill="#cccccc", outline=""
        )
        self.map_canvas.create_rectangle(
            legend_x, legend_y, legend_x + legend_width, legend_y + legend_height,
            fill="white", outline=Style.ACCENT_COLOR, width=2
        )
        
        # Legend title
        title_y = legend_y + 15
        self.map_canvas.create_text(
            legend_x + legend_width // 2, title_y, 
            text="📊 Network Legend", font=Style.FONT_BOLD, 
            fill=Style.ACCENT_COLOR
        )
        
        current_y = title_y + 25
        
        # Topics section
        current_y = self._draw_legend_section(
            "📌 Topics", self.topic_palette.items(), legend_x, current_y, legend_width,
            lambda item: self._draw_topic_marker(legend_x + 10, current_y, item[1], item[0])
        )
        
        # PHY section
        phy_items = [(phy, count) for phy, count in phy_counts.items()]
        current_y = self._draw_legend_section(
            "📡 Protocols", phy_items, legend_x, current_y, legend_width,
            lambda item: self._draw_phy_marker(legend_x + 10, current_y, item[0], item[1])
        )
        
        # Connection states section
        state_items = [(state, count) for state, count in connection_states.items() if count > 0]
        current_y = self._draw_legend_section(
            "🔗 Connection States", state_items, legend_x, current_y, legend_width,
            lambda item: self._draw_state_marker(legend_x + 10, current_y, item[0], item[1])
        )
        
        # Gateway info
        self._draw_gateway_legend(legend_x, current_y, legend_width)

    def _draw_legend_section(self, title: str, items: List, legend_x: int, start_y: int, legend_width: int, draw_marker_func) -> int:
        """Draw a section of the legend and return the next Y position."""
        current_y = start_y
        
        # Section title
        self.map_canvas.create_text(
            legend_x + 10, current_y, text=title, 
            anchor=tk.W, font=Style.FONT_BOLD, fill=Style.TEXT_COLOR
        )
        current_y += 18
        
        # Section items
        for item in items:
            draw_marker_func(item)
            current_y += 18
        
        return current_y + 10

    def _draw_topic_marker(self, x: int, y: int, color: str, topic: str) -> None:
        """Draw a topic marker in the legend."""
        self.map_canvas.create_rectangle(x, y - 6, x + 12, y + 6, fill=color, outline="black")
        self.map_canvas.create_text(x + 20, y, text=topic.split('/')[-1], anchor=tk.W, font=Style.FONT_SMALL)

    def _draw_phy_marker(self, x: int, y: int, phy: str, count: int) -> None:
        """Draw a PHY protocol marker in the legend."""
        size = {"BLE": 6, "ZIGBEE": 8, "WIFI": 10}.get(phy, 7)
        color = {"BLE": Style.SUCCESS_COLOR, "ZIGBEE": Style.WARNING_COLOR, "WIFI": Style.ACCENT_COLOR}.get(phy, "#cccccc")
        symbol = {"BLE": "B", "ZIGBEE": "Z", "WIFI": "W"}.get(phy, "?")
        
        self.map_canvas.create_oval(x, y - size, x + size * 2, y + size, fill=color, outline="black")
        self.map_canvas.create_text(x + size, y, text=symbol, font=("Arial", 6, "bold"), fill="white")
        self.map_canvas.create_text(x + 25, y, text=f"{phy}: {count}", anchor=tk.W, font=Style.FONT_SMALL)

    def _draw_state_marker(self, x: int, y: int, state: str, count: int) -> None:
        """Draw a connection state marker in the legend."""
        colors = {"connected": "green", "disconnected": "red", "reconnecting": "orange"}
        symbols = {"connected": "●", "disconnected": "○", "reconnecting": "◐"}
        
        color = colors.get(state, "gray")
        symbol = symbols.get(state, "?")
        
        self.map_canvas.create_text(x + 5, y, text=symbol, font=Style.FONT_NORMAL, fill=color)
        self.map_canvas.create_text(x + 20, y, text=f"{state}: {count}", anchor=tk.W, font=Style.FONT_SMALL)

    def _draw_gateway_legend(self, legend_x: int, y: int, legend_width: int) -> None:
        """Draw gateway legend section."""
        self.map_canvas.create_text(
            legend_x + 10, y, text="📡 Gateway Coverage", 
            anchor=tk.W, font=Style.FONT_BOLD, fill=Style.TEXT_COLOR
        )
        y += 18
        
        # Coverage area indicator
        self.map_canvas.create_line(
            legend_x + 10, y, legend_x + 30, y, 
            fill="#cccccc", dash=(4, 2), width=2
        )
        self.map_canvas.create_text(
            legend_x + 35, y, text="Coverage Range", 
            anchor=tk.W, font=Style.FONT_SMALL
        )


    # Results management helpers

    def clear_results(self) -> None:
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

    def run_selected_result(self) -> None:
        """Re-run a selected result from the results table."""
        selected = self.results_tree.selection()
        if not selected:
            messagebox.showinfo("Results", "Select a result row to rerun.")
            return
        if self.running:
            messagebox.showwarning("Running", "Please wait for current simulation to complete.")
            return
        scenario = self.results_tree.item(selected[0], "values")[0]
        self.current_run = {"scenario": scenario}
        self._trigger_run()

    # Composite Experiment Methods
    def run_e1_experiment(self) -> None:
        """Run E1: Duty Cycle Impact Study - baseline vs duty_cycle scenarios."""
        if self.running:
            messagebox.showwarning("Running", "Please wait for current simulation to complete.")
            return
        
        self.composite_results["E1"] = []
        scenarios = ["baseline", "duty_cycle"]
        self._run_composite_experiment("E1", scenarios)

    def run_e2_experiment(self) -> None:
        """Run E2: Protocol Comparison Study - BLE vs WiFi vs Zigbee scenarios."""
        if self.running:
            messagebox.showwarning("Running", "Please wait for current simulation to complete.")
            return
        
        self.composite_results["E2"] = []
        scenarios = ["ble_only", "wifi_only", "zigbee_only"]
        self._run_composite_experiment("E2", scenarios)

    def run_e3_experiment(self) -> None:
        """Run E3: Topology & Broker Failure Study - baseline vs topology_failover scenarios."""
        if self.running:
            messagebox.showwarning("Running", "Please wait for current simulation to complete.")
            return
        
        self.composite_results["E3"] = []
        scenarios = ["baseline", "topology_failover"]
        self._run_composite_experiment("E3", scenarios)

    def _run_composite_experiment(self, experiment_name: str, scenarios: List[str]) -> None:
        """Run a composite experiment with multiple scenarios."""
        self.current_composite = {"experiment": experiment_name, "scenarios": scenarios, "current_index": 0}
        self._run_next_composite_scenario()

    def _run_next_composite_scenario(self) -> None:
        """Run the next scenario in a composite experiment."""
        composite = self.current_composite
        if composite["current_index"] >= len(composite["scenarios"]):
            # All scenarios completed, display results
            self._display_composite_results(composite["experiment"])
            self.current_composite = None
            return
        
        scenario = composite["scenarios"][composite["current_index"]]
        self.current_run = {
            "scenario": scenario,
            "composite_experiment": composite["experiment"],
            "composite_index": composite["current_index"],
        }
        self._trigger_run()

    def _update_gui_after_run(self) -> None:
        self.stop_simulation()
        if not self.snapshots:
            return
            
        if self.current_run:
            last = self.snapshots[-1]
            
            # Handle composite experiment results
            if "composite_experiment" in self.current_run:
                experiment_name = self.current_run["composite_experiment"]
                scenario_name = self.current_run["scenario"]
                summary = compute_summary_stats(self.snapshots, scenario_name)
                self.composite_results[experiment_name].append(summary)
                
                # Continue with next scenario in composite experiment
                self.current_composite["current_index"] += 1
                self.current_run = None
                self.root.after(1000, self._run_next_composite_scenario)  # Small delay between runs
                return
            
            # Regular single scenario result
            self.results_tree.insert(
                "",
                tk.END,
                values=(
                    self.current_run["scenario"],
                    f"{last.delivery_ratio*100:.1f}",
                    f"{last.avg_latency_ms:.1f}",
                    last.duplicates,
                    f"{last.energy_consumed_mj:.1f}",
                ),
            )
            self.current_run = None
            
        self.snapshot_index = 0
        self._playback_snapshots()

    def _display_composite_results(self, experiment_name: str) -> None:
        """Display comparison table and commentary for a composite experiment."""
        if experiment_name not in self.composite_results or not self.composite_results[experiment_name]:
            return
            
        # Clear previous results in scrollable frame
        for widget in self.composite_scrollable_frame.winfo_children():
            if str(widget).endswith(f"_{experiment_name.lower()}"):
                widget.destroy()
        
        # Create experiment results frame
        exp_frame = ttk.LabelFrame(self.composite_scrollable_frame, text=f"{experiment_name} Results", name=f"frame_{experiment_name.lower()}")
        exp_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add experiment description
        desc_label = ttk.Label(exp_frame, text=self.composite_experiment_notes[experiment_name], 
                              wraplength=500, font=("Arial", 9))
        desc_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # Create comparison table
        table_frame = ttk.Frame(exp_frame)
        table_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Table headers
        headers = ["Scenario", "Delivery %", "Latency (ms)", "Energy (mJ)", "Battery (days)", "Commentary"]
        columns = len(headers)
        
        for col, header in enumerate(headers):
            label = ttk.Label(table_frame, text=header, font=("Arial", 9, "bold"), relief="ridge", width=12)
            label.grid(row=0, column=col, sticky="ew", padx=1, pady=1)
        
        # Table data
        results = self.composite_results[experiment_name]
        for row, summary in enumerate(results, 1):
            battery_str = f"{summary.avg_battery_days:.1f}" if summary.avg_battery_days != float("inf") else "∞"
            commentary = self._get_scenario_commentary(experiment_name, summary.scenario, summary)
            
            values = [
                summary.scenario,
                f"{summary.delivery_ratio*100:.1f}",
                f"{summary.avg_latency_ms:.1f}",
                f"{summary.energy_consumed_mj:.1f}",
                battery_str,
                commentary
            ]
            
            for col, value in enumerate(values):
                if col == len(values) - 1:  # Commentary column
                    label = ttk.Label(table_frame, text=value, wraplength=150, font=("Arial", 8), relief="ridge")
                else:
                    label = ttk.Label(table_frame, text=value, font=("Arial", 9), relief="ridge", width=12)
                label.grid(row=row, column=col, sticky="ew", padx=1, pady=1)
        
        # Configure column weights
        for col in range(columns):
            table_frame.grid_columnconfigure(col, weight=1)
        
        # Add overall analysis
        analysis_text = self._get_experiment_analysis(experiment_name, results)
        analysis_label = ttk.Label(exp_frame, text=f"Analysis: {analysis_text}", 
                                  wraplength=500, font=("Arial", 9, "italic"))
        analysis_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Update scroll region
        self.composite_canvas.configure(scrollregion=self.composite_canvas.bbox("all"))

    def _get_scenario_commentary(self, experiment: str, scenario: str, summary: ExperimentSummary) -> str:
        """Generate specific commentary for a scenario within an experiment."""
        if experiment == "E1":
            if scenario == "baseline":
                return "Normal operation with 10% duty cycle"
            elif scenario == "duty_cycle":
                energy_ratio = summary.energy_consumed_mj / (self.composite_results["E1"][0].energy_consumed_mj + 1e-6)
                latency_ratio = summary.avg_latency_ms / (self.composite_results["E1"][0].avg_latency_ms + 1e-6)
                return f"5% duty cycle: {energy_ratio:.2f}x energy, {latency_ratio:.2f}x latency"
        elif experiment == "E2":
            if scenario == "ble_only":
                return "BLE only: Low power, moderate range"
            elif scenario == "wifi_only":
                return "WiFi only: High power, high throughput"
            elif scenario == "zigbee_only":
                return "Zigbee only: Ultra-low power, mesh capable"
        elif experiment == "E3":
            if scenario == "baseline":
                return "Stable network operation"
            elif scenario == "topology_failover":
                message_loss = summary.send_events - summary.delivery_events
                return f"With failures: {message_loss} messages lost"
        return "N/A"

    def _get_experiment_analysis(self, experiment: str, results: List[ExperimentSummary]) -> str:
        """Generate overall analysis for the experiment."""
        if len(results) < 2:
            return "Insufficient data for comparison."
        
        baseline = results[0]
        comparison = results[1]
        
        if experiment == "E1":
            energy_improvement = (baseline.energy_consumed_mj - comparison.energy_consumed_mj) / baseline.energy_consumed_mj * 100
            latency_change = (comparison.avg_latency_ms - baseline.avg_latency_ms) / baseline.avg_latency_ms * 100
            battery_improvement = (comparison.avg_battery_days - baseline.avg_battery_days) / baseline.avg_battery_days * 100 if baseline.avg_battery_days != float("inf") else 0
            
            return f"Duty cycle reduction saves {energy_improvement:.1f}% energy, extends battery life {battery_improvement:.1f}%, but increases latency {latency_change:.1f}%."
        
        elif experiment == "E2":
            if len(results) >= 3:
                ble_result = results[0]  # ble_only
                wifi_result = results[1]  # wifi_only
                zigbee_result = results[2]  # zigbee_only
                
                # Find best and worst for each metric
                energy_sorted = sorted(results, key=lambda x: x.energy_consumed_mj)
                latency_sorted = sorted(results, key=lambda x: x.avg_latency_ms)
                delivery_sorted = sorted(results, key=lambda x: x.delivery_ratio, reverse=True)
                
                return f"Protocol comparison: {energy_sorted[0].scenario} most energy efficient, {latency_sorted[0].scenario} lowest latency, {delivery_sorted[0].scenario} best delivery. WiFi consumes {wifi_result.energy_consumed_mj/ble_result.energy_consumed_mj:.1f}x more energy than BLE."
            else:
                return f"Protocol comparison with {len(results)} protocols completed."
        
        elif experiment == "E3":
            msg_loss_baseline = baseline.send_events - baseline.delivery_events
            msg_loss_failure = comparison.send_events - comparison.delivery_events
            additional_loss = msg_loss_failure - msg_loss_baseline
            recovery_impact = (baseline.delivery_ratio - comparison.delivery_ratio) * 100
            
            return f"Failures caused {additional_loss} additional message losses, reducing delivery ratio by {recovery_impact:.1f}%. System shows {'good' if recovery_impact < 5 else 'poor'} resilience."
        
        return "Analysis complete."

    def clear_composite_results(self) -> None:
        """Clear all composite experiment results."""
        self.composite_results.clear()
        for widget in self.composite_scrollable_frame.winfo_children():
            widget.destroy()
        self.composite_canvas.configure(scrollregion=self.composite_canvas.bbox("all"))

    def export_composite_results(self) -> None:
        """Export composite experiment results to CSV."""
        if not self.composite_results:
            messagebox.showwarning("No data", "Run some composite experiments first")
            return
            
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
            
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("experiment,scenario,delivery_ratio,avg_latency_ms,duplicates,energy_mj,avg_battery_days,send_events,delivery_events\n")
            for exp_name, results in self.composite_results.items():
                for summary in results:
                    fh.write(f"{exp_name},{summary.scenario},{summary.delivery_ratio:.4f},{summary.avg_latency_ms:.2f},"
                            f"{summary.duplicates},{summary.energy_consumed_mj:.3f},{summary.avg_battery_days:.2f},"
                            f"{summary.send_events},{summary.delivery_events}\n")
        messagebox.showinfo("Export", f"Composite results saved to {path}")


def launch_app(config_factory) -> None:
    root = tk.Tk()
    app = IoTMQTTApp(root, config_factory)
    root.mainloop()


