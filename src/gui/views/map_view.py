import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches
import numpy as np


class InteractiveMapView(tk.Frame):
    def __init__(self, parent, on_node_click, on_bg_click, on_node_move, on_wall_drawn):
        super().__init__(parent, bg="white")
        self.on_node_click = on_node_click
        self.on_bg_click = on_bg_click
        self.on_node_move = on_node_move
        self.nodes_cache = []
        self.selected_node_id = None
        self.dragging_node = None

        # Viewport State
        self.xlim = [0, 500]
        self.ylim = [0, 500]
        self.is_panning = False
        self.pan_start = None

        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.fig.patch.set_facecolor('white')
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Bindings
        self.canvas.mpl_connect('button_press_event', self._on_press)
        self.canvas.mpl_connect('button_release_event', self._on_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_drag)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)

        self._setup_ax()

    def update_state(self, nodes, walls, selected_id, queue_history, topic_counts=None):
        self.nodes_cache = nodes
        self.selected_node_id = selected_id
        if not self.dragging_node and not self.is_panning:
            self._draw_map()

    def _draw_map(self):
        self.ax.clear()
        self._setup_ax()

        styles = {
            'Gateway': {'c': '#8e44ad', 'm': '^', 's': 250},
            'Sensor': {'c': '#27ae60', 'm': 'o', 's': 120},
            'iPhone': {'c': '#2980b9', 'm': 's', 's': 110},
            'Laptop': {'c': '#e67e22', 'm': 'D', 's': 120},
            'Asset Tag': {'c': '#16a085', 'm': 'p', 's': 140},
            'Beacon': {'c': '#f1c40f', 'm': '*', 's': 150},
            'Wearable': {'c': '#d35400', 'm': 'h', 's': 110},
        }

        # Lookup for line drawing
        node_pos = {n['id']: (n['x'], n['y']) for n in self.nodes_cache}

        for n in self.nodes_cache:
            is_active = (n['state'] == 'active')
            st = styles.get(n['type'], styles['Sensor'])
            base_color = st['c']
            status_color = '#2ecc71' if is_active else '#e74c3c'

            # 1. CONNECTION LINES (New)
            if is_active and n.get('parent_id') and n['parent_id'] in node_pos:
                px, py = node_pos[n['parent_id']]
                self.ax.plot([n['x'], px], [n['y'], py], color='#95a5a6', linestyle='-', linewidth=1, alpha=0.6,
                             zorder=1)

            # 2. Range Circle
            if 'range' in n:
                fill_color = status_color
                alpha = 0.08 if is_active else 0.04
                circle = patches.Circle((n['x'], n['y']), n['range'], color=fill_color, alpha=alpha, linestyle='-',
                                        linewidth=1, ec=status_color)
                self.ax.add_patch(circle)

            # 3. Selection Ring
            if n['id'] == self.selected_node_id:
                ring = patches.Circle((n['x'], n['y']), 12, color='#3498db', fill=False, lw=2, zorder=5)
                self.ax.add_patch(ring)

            # 4. Node Body
            face_color = base_color if n['type'] == 'Gateway' else status_color
            self.ax.scatter(n['x'], n['y'], c=face_color, marker=st['m'], s=st['s'], edgecolors='white', linewidths=1.5,
                            zorder=10)
            self.ax.text(n['x'], n['y'] + 18, n['id'], fontsize=8, ha='center', fontweight='bold', color='#555',
                         zorder=12)

        self.canvas.draw()

    def _setup_ax(self):
        self.ax.set_xlim(self.xlim)
        self.ax.set_ylim(self.ylim)
        self.ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.2, color='#2c3e50')
        self.ax.set_facecolor('white')
        for spine in self.ax.spines.values(): spine.set_visible(False)
        self.ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # --- Interaction Handlers ---
    def _on_scroll(self, event):
        """Zoom Logic"""
        if event.inaxes != self.ax: return
        base_scale = 1.1
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata

        if event.button == 'up':
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            scale_factor = base_scale
        else:
            scale_factor = 1

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        self.xlim = [xdata - new_width * (1 - relx), xdata + new_width * (relx)]
        self.ylim = [ydata - new_height * (1 - rely), ydata + new_height * (rely)]

        self.ax.set_xlim(self.xlim)
        self.ax.set_ylim(self.ylim)
        self.canvas.draw()

    def _on_press(self, event):
        if event.inaxes != self.ax: return

        # Right Click (3) or Middle Click (2) -> Pan
        if event.button in [2, 3]:
            self.is_panning = True
            self.pan_start = (event.xdata, event.ydata)
            return

        # Left Click -> Select/Drag Node
        clicked = None
        # Adjust click detection for current zoom level
        zoom_factor = (self.xlim[1] - self.xlim[0]) / 500
        click_radius = 20 * zoom_factor

        for n in self.nodes_cache:
            if np.sqrt((n['x'] - event.xdata) ** 2 + (n['y'] - event.ydata) ** 2) < click_radius:
                clicked = n;
                break

        if clicked:
            self.dragging_node = clicked
            self.on_node_click(clicked['id'])
        else:
            self.on_bg_click(event.xdata, event.ydata)

    def _on_drag(self, event):
        if event.inaxes != self.ax: return

        if self.is_panning and self.pan_start:
            dx = event.xdata - self.pan_start[0]
            dy = event.ydata - self.pan_start[1]
            self.xlim = [x - dx for x in self.xlim]
            self.ylim = [y - dy for y in self.ylim]
            self.ax.set_xlim(self.xlim)
            self.ax.set_ylim(self.ylim)
            self.canvas.draw()
            return

        if self.dragging_node:
            self.dragging_node['x'] = event.xdata
            self.dragging_node['y'] = event.ydata
            self._draw_map()

    def _on_release(self, event):
        self.is_panning = False
        self.pan_start = None
        if self.dragging_node:
            self.on_node_move(self.dragging_node['id'], self.dragging_node['x'], self.dragging_node['y'])
            self.dragging_node = None