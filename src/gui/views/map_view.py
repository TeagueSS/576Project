import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# Import other views
from .topic_heatmap import TopicHeatmap
from .queue_sparkline import QueueSparkline


class InteractiveMapView(tk.Frame):
    def __init__(self, parent, on_node_click, on_bg_click, on_node_move, on_wall_drawn):
        super().__init__(parent)
        self.on_node_click = on_node_click
        self.on_bg_click = on_bg_click
        self.on_node_move = on_node_move
        self.on_wall_drawn = on_wall_drawn

        self.mode = "map"  # 'map', 'draw_wall', 'table', 'queue'
        self.nodes_cache = []
        self.walls_cache = []
        self.selected_node_id = None

        self.dragging_node = None
        self.wall_start_point = None

        # Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Layer 1: Map ---
        self.map_frame = tk.Frame(self, bg="white")
        self.map_frame.grid(row=0, column=0, sticky="nsew")

        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Events
        self.fig.canvas.mpl_connect('button_press_event', self._on_press)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_drag)
        self.fig.canvas.mpl_connect('button_release_event', self._on_release)

        # --- Layer 2: Table ---
        self.table_frame = tk.Frame(self, bg="#eee")
        self.table_frame.grid(row=0, column=0, sticky="nsew")
        cols = ("ID", "Type", "IP", "State", "Position")
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90)
        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # --- Layer 3: Queue ---
        self.queue_frame = tk.Frame(self)
        self.queue_frame.grid(row=0, column=0, sticky="nsew")
        self.queue_view = QueueSparkline(self.queue_frame)
        self.queue_view.pack(fill=tk.BOTH, expand=True)

        # --- Layer 4: Heatmap ---
        self.heatmap_frame = tk.Frame(self)
        self.heatmap_frame.grid(row=0, column=0, sticky="nsew")
        self.heatmap_view = TopicHeatmap(self.heatmap_frame)
        self.heatmap_view.pack(fill=tk.BOTH, expand=True)

        # Init
        self.set_mode("map")
        self._setup_ax()

    def set_mode(self, mode):
        self.mode = mode
        if mode in ['map', 'draw_wall']:
            self.map_frame.tkraise()
            self._draw_map()
        elif mode == 'table':
            self.table_frame.tkraise()
            self._refresh_table()
        elif mode == 'queue':
            self.queue_frame.tkraise()
        elif mode == 'heatmap':
            self.heatmap_frame.tkraise()

    def update_state(self, nodes, walls, selected_id, queue_history, topic_counts=None):
        self.nodes_cache = nodes
        self.walls_cache = walls
        self.selected_node_id = selected_id
        self.topic_cache = topic_counts if topic_counts else {}

        if self.mode == 'queue':
            self.queue_view.update_plot(queue_history)
        elif self.mode == 'heatmap':
            self.heatmap_view.update_plot(self.topic_cache)
        elif self.mode == 'table':
            self._refresh_table()
        elif self.mode in ['map', 'draw_wall']:
            if not self.dragging_node and not self.wall_start_point:
                self._draw_map()

    def _draw_map(self):
        self.ax.clear()
        self._setup_ax()

        # 1. Draw Walls (Thick architectural lines)
        for w in self.walls_cache:
            self.ax.plot([w[0][0], w[1][0]], [w[0][1], w[1][1]], color='#2c3e50', linewidth=4, solid_capstyle='round',
                         alpha=0.9)

        # 2. Draw Coverage Heatmap (if node selected)
        if self.selected_node_id:
            source = next((n for n in self.nodes_cache if n['id'] == self.selected_node_id), None)
            if source and source['type'] in ['Gateway', 'Sensor']:  # Only radios emit signal
                self._draw_signal_heatmap(source)

        # 3. Draw Nodes
        styles = {
            'Gateway': {'c': '#8e44ad', 'm': '^', 's': 180},
            'Sensor': {'c': '#27ae60', 'm': 'o', 's': 80},
            'iPhone': {'c': '#2980b9', 'm': 's', 's': 70},
            'Laptop': {'c': '#e67e22', 'm': 'D', 's': 80}
        }

        for n in self.nodes_cache:
            style = styles.get(n['type'], {'c': 'gray', 'm': 'o', 's': 40})
            # Highlight selected
            is_selected = (n['id'] == self.selected_node_id)
            edgecolor = '#e74c3c' if is_selected else 'white'
            linewidth = 2.5 if is_selected else 1

            # Draw connection lines if selected (Logical links, not just signal)
            if is_selected and n['type'] == 'Gateway':
                for other in self.nodes_cache:
                    if other['id'] != n['id']:
                        self.ax.plot([n['x'], other['x']], [n['y'], other['y']], color='orange', linewidth=1, alpha=0.4,
                                     linestyle=':')

            self.ax.scatter(n['x'], n['y'],
                            c=style['c'], marker=style['m'], s=style['s'],
                            edgecolors=edgecolor, linewidths=linewidth,
                            label=n['type'], picker=True, zorder=10)

            # ID Tag
            self.ax.text(n['x'] + 4, n['y'] - 4, n['id'], fontsize=8, weight='bold', zorder=11,
                         bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        self.canvas.draw()

    def _draw_signal_heatmap(self, source):
        """
        Generates a grid of signal strength values, simulating wall shadowing.
        Renders a contour map (Green > Yellow > Red).
        """
        GRID_RES = 40  # Resolution (higher = smoother but slower)
        x = np.linspace(0, 200, GRID_RES)
        y = np.linspace(0, 200, GRID_RES)
        X, Y = np.meshgrid(x, y)

        # Tx Power & Constants
        TX_POWER = source.get('strength', 20.0)  # dBm
        WALL_PENALTY = 15.0  # dB loss per wall
        PATH_LOSS_EXP = 2.5

        # Flatten for calculation
        xf, yf = X.flatten(), Y.flatten()
        signal_strength = np.zeros_like(xf)

        src_pos = np.array([source['x'], source['y']])

        # Calculate signal at every grid point
        for i in range(len(xf)):
            target_pos = np.array([xf[i], yf[i]])
            dist = np.linalg.norm(target_pos - src_pos)
            if dist < 1: dist = 1  # Avoid log(0)

            # 1. Free Space Path Loss model
            loss = 20 * np.log10(dist)  # Simple log distance

            # 2. Wall Shadowing (Ray Casting)
            wall_hits = 0
            for w in self.walls_cache:
                if self._lines_intersect(src_pos, target_pos, np.array(w[0]), np.array(w[1])):
                    wall_hits += 1

            total_rssi = TX_POWER - loss - (wall_hits * WALL_PENALTY)
            signal_strength[i] = total_rssi

        Z = signal_strength.reshape(X.shape)

        # Render Contour
        # Levels: Strong (> -60), Good (> -75), Weak (> -90), Dead (< -90)
        levels = [-100, -85, -70, -50, 100]
        colors = ['#e74c3c', '#f1c40f', '#2ecc71', '#2ecc71']  # Red, Yellow, Green

        self.ax.contourf(X, Y, Z, levels=levels, colors=colors, alpha=0.3, extend='both', zorder=1)

    def _lines_intersect(self, a, b, c, d):
        """Returns True if line segments ab and cd intersect."""

        def ccw(p1, p2, p3):
            return (p3[1] - p1[1]) * (p2[0] - p1[0]) > (p2[1] - p1[1]) * (p3[0] - p1[0])

        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

    def _refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for n in self.nodes_cache:
            pos_str = f"({n['x']:.0f}, {n['y']:.0f})"
            self.tree.insert("", "end", values=(n['id'], n['type'], n['ip'], n['state'], pos_str))

    def _setup_ax(self):
        self.ax.set_xlim(0, 200)
        self.ax.set_ylim(0, 200)
        self.ax.grid(True, linestyle=':', alpha=0.3, color='#bdc3c7')
        self.ax.set_facecolor('#ecf0f1')  # Blueprint-ish background
        self.ax.set_xticks([])  # Hide ticks for cleaner look
        self.ax.set_yticks([])

    # --- Interactions ---
    def _on_press(self, event):
        if event.inaxes != self.ax: return

        if self.mode == 'draw_wall':
            self.wall_start_point = (event.xdata, event.ydata)
        else:
            # Node Selection / Drag Start
            clicked = None
            for n in self.nodes_cache:
                if np.sqrt((n['x'] - event.xdata) ** 2 + (n['y'] - event.ydata) ** 2) < 10:
                    clicked = n
                    break

            if clicked:
                self.dragging_node = clicked
                self.on_node_click(clicked['id'])
            else:
                self.on_bg_click(event.xdata, event.ydata)

    def _on_drag(self, event):
        if event.inaxes != self.ax: return

        if self.mode == 'draw_wall' and self.wall_start_point:
            # Visual preview of wall
            self.ax.clear()
            self._setup_ax()
            self._draw_map()
            # Draw temp line
            self.ax.plot([self.wall_start_point[0], event.xdata],
                         [self.wall_start_point[1], event.ydata],
                         color='#2c3e50', linestyle='--', linewidth=3)
            self.canvas.draw()

        elif self.dragging_node:
            self.dragging_node['x'] = event.xdata
            self.dragging_node['y'] = event.ydata
            self._draw_map()

    def _on_release(self, event):
        if self.mode == 'draw_wall' and self.wall_start_point:
            # Finalize Wall
            start = self.wall_start_point
            end = (event.xdata, event.ydata)
            self.on_wall_drawn(start, end)
            self.wall_start_point = None
            self._draw_map()

        elif self.dragging_node:
            self.on_node_move(self.dragging_node['id'], self.dragging_node['x'], self.dragging_node['y'])
            self.dragging_node = None