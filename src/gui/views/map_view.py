import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import heapq

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

        self.mode = "map"
        self.nodes_cache = []
        self.walls_cache = []
        self.selected_node_id = None
        self.is_adhoc_mode = False

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

    def set_adhoc_mode(self, enabled):
        self.is_adhoc_mode = enabled
        self._draw_map()

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

        # 1. Draw Walls
        for w in self.walls_cache:
            self.ax.plot([w[0][0], w[1][0]], [w[0][1], w[1][1]], color='#2c3e50', linewidth=4, solid_capstyle='round',
                         alpha=0.9)

        # 2. Ad-Hoc Path Visualization
        if self.is_adhoc_mode:
            self._draw_adhoc_path()
        elif self.selected_node_id:
            source = next((n for n in self.nodes_cache if n['id'] == self.selected_node_id), None)
            if source and source['type'] in ['Gateway', 'Sensor', 'Source Node', 'Ad-Hoc Relay', 'Wi-Fi_GW']:
                self._draw_signal_heatmap(source)

        # 3. Draw Nodes
        styles = {
            'Gateway': {'c': '#8e44ad', 'm': '^', 's': 180},
            'Sensor': {'c': '#27ae60', 'm': 'o', 's': 80},
            'iPhone': {'c': '#2980b9', 'm': 's', 's': 70},
            'Laptop': {'c': '#e67e22', 'm': 'D', 's': 80},
            'Ad-Hoc Relay': {'c': '#16a085', 'm': 'p', 's': 100},
            'Source Node': {'c': '#2ecc71', 'm': '*', 's': 200},
            'Sink Node': {'c': '#e74c3c', 'm': 'X', 's': 150}
        }

        for n in self.nodes_cache:
            style = styles.get(n['type'], {'c': 'gray', 'm': 'o', 's': 40})
            is_selected = (n['id'] == self.selected_node_id)
            edgecolor = '#e74c3c' if is_selected else 'white'
            linewidth = 2.5 if is_selected else 1

            self.ax.scatter(n['x'], n['y'],
                            c=style['c'], marker=style['m'], s=style['s'],
                            edgecolors=edgecolor, linewidths=linewidth,
                            label=n['type'], picker=True, zorder=10)

            self.ax.text(n['x'] + 4, n['y'] - 4, n['id'], fontsize=8, weight='bold', zorder=11,
                         bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        self.canvas.draw()

    def _draw_adhoc_path(self):
        source = next((n for n in self.nodes_cache if n['type'] == 'Source Node'), None)
        sink = next((n for n in self.nodes_cache if n['type'] == 'Sink Node'), None)

        if not source or not sink: return

        graph = {n['id']: [] for n in self.nodes_cache}
        positions = {n['id']: (n['x'], n['y']) for n in self.nodes_cache}

        for i, n1 in enumerate(self.nodes_cache):
            for n2 in self.nodes_cache[i + 1:]:
                dist = np.linalg.norm(np.array(positions[n1['id']]) - np.array(positions[n2['id']]))
                blocked = False
                for w in self.walls_cache:
                    if self._lines_intersect(positions[n1['id']], positions[n2['id']], w[0], w[1]):
                        blocked = True;
                        break

                if dist < 80 and not blocked:
                    graph[n1['id']].append(n2['id'])
                    graph[n2['id']].append(n1['id'])
                    # Visualize Links
                    u, v = positions[n1['id']], positions[n2['id']]
                    self.ax.plot([u[0], v[0]], [u[1], v[1]], color='#bdc3c7', linestyle=':', alpha=0.5, zorder=1)

        queue = [(0, source['id'], [])]
        visited = set()
        final_path = None

        while queue:
            cost, curr, path = heapq.heappop(queue)
            if curr in visited: continue
            visited.add(curr)
            path = path + [curr]
            if curr == sink['id']:
                final_path = path
                break
            for neighbor in graph[curr]:
                if neighbor not in visited:
                    heapq.heappush(queue, (cost + 1, neighbor, path))

        if final_path:
            for i in range(len(final_path) - 1):
                u, v = positions[final_path[i]], positions[final_path[i + 1]]
                self.ax.plot([u[0], v[0]], [u[1], v[1]], color='#3498db', linewidth=3, linestyle='-', alpha=0.8,
                             zorder=5)

    def _draw_signal_heatmap(self, source):
        GRID_RES = 40
        x = np.linspace(0, 200, GRID_RES)
        y = np.linspace(0, 200, GRID_RES)
        X, Y = np.meshgrid(x, y)

        TX_POWER = source.get('strength', 20.0)
        WALL_PENALTY = 15.0

        xf, yf = X.flatten(), Y.flatten()
        signal_strength = np.zeros_like(xf)
        src_pos = np.array([source['x'], source['y']])

        for i in range(len(xf)):
            target_pos = np.array([xf[i], yf[i]])
            dist = np.linalg.norm(target_pos - src_pos)
            if dist < 1: dist = 1
            loss = 20 * np.log10(dist)
            wall_hits = 0
            for w in self.walls_cache:
                if self._lines_intersect(src_pos, target_pos, np.array(w[0]), np.array(w[1])):
                    wall_hits += 1
            signal_strength[i] = TX_POWER - loss - (wall_hits * WALL_PENALTY)

        Z = signal_strength.reshape(X.shape)
        levels = [-100, -85, -70, -50, 100]
        colors = ['#e74c3c', '#f1c40f', '#2ecc71', '#2ecc71']
        self.ax.contourf(X, Y, Z, levels=levels, colors=colors, alpha=0.3, extend='both', zorder=1)

    def _lines_intersect(self, a, b, c, d):
        a, b, c, d = np.array(a), np.array(b), np.array(c), np.array(d)

        def ccw(p1, p2, p3):
            return (p3[1] - p1[1]) * (p2[0] - p1[0]) > (p2[1] - p1[1]) * (p3[0] - p1[0])

        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

    def _refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for n in self.nodes_cache:
            pos_str = f"({n['x']:.0f}, {n['y']:.0f})"
            # KEY FIX: Use .get() with default to prevent KeyError
            ip_val = n.get('ip', 'N/A')
            self.tree.insert("", "end", values=(n['id'], n['type'], ip_val, n['state'], pos_str))

    def _setup_ax(self):
        self.ax.set_xlim(0, 200)
        self.ax.set_ylim(0, 200)
        self.ax.grid(True, linestyle=':', alpha=0.3, color='#bdc3c7')
        self.ax.set_facecolor('#ecf0f1')
        self.ax.set_xticks([])
        self.ax.set_yticks([])

    def _on_press(self, event):
        if event.inaxes != self.ax: return
        if self.mode == 'draw_wall':
            self.wall_start_point = (event.xdata, event.ydata)
        else:
            clicked = None
            for n in self.nodes_cache:
                if np.sqrt((n['x'] - event.xdata) ** 2 + (n['y'] - event.ydata) ** 2) < 10:
                    clicked = n;
                    break
            if clicked:
                self.dragging_node = clicked
                self.on_node_click(clicked['id'])
            else:
                self.on_bg_click(event.xdata, event.ydata)

    def _on_drag(self, event):
        if event.inaxes != self.ax: return
        if self.mode == 'draw_wall' and self.wall_start_point:
            self.ax.clear();
            self._setup_ax();
            self._draw_map()
            self.ax.plot([self.wall_start_point[0], event.xdata], [self.wall_start_point[1], event.ydata],
                         color='#2c3e50', linestyle='--', linewidth=3)
            self.canvas.draw()
        elif self.dragging_node:
            self.dragging_node['x'] = event.xdata
            self.dragging_node['y'] = event.ydata
            self._draw_map()

    def _on_release(self, event):
        if self.mode == 'draw_wall' and self.wall_start_point:
            self.on_wall_drawn(self.wall_start_point, (event.xdata, event.ydata))
            self.wall_start_point = None
            self._draw_map()
        elif self.dragging_node:
            self.on_node_move(self.dragging_node['id'], self.dragging_node['x'], self.dragging_node['y'])
            self.dragging_node = None