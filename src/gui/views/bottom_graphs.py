import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque


class BottomAnalysisPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Grid: 1 Row, 3 Columns
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        # Graph 1
        self.g1 = SingleGraphWidget(self, "Graph 1", ["Throughput", "Latency"])
        self.g1.grid(row=0, column=0, sticky="nsew", padx=2)

        # Graph 2
        self.g2 = SingleGraphWidget(self, "Graph 2", ["Queue Depth", "Packet Loss"])
        self.g2.grid(row=0, column=1, sticky="nsew", padx=2)

        # Graph 3
        self.g3 = SingleGraphWidget(self, "Graph 3", ["Energy", "Active Nodes"])
        self.g3.grid(row=0, column=2, sticky="nsew", padx=2)

    def update_data(self, val1, val2, val3):
        self.g1.add_point(val1)
        self.g2.add_point(val2)
        self.g3.add_point(val3)


class SingleGraphWidget(ttk.Frame):
    def __init__(self, parent, title, options):
        super().__init__(parent, relief="sunken", borderwidth=1)

        # Header: Dropdown
        self.type_var = tk.StringVar(value=options[0])
        cb = ttk.Combobox(self, textvariable=self.type_var, values=options, state="readonly")
        cb.pack(fill="x", padx=5, pady=2)

        # Plot
        self.fig = Figure(figsize=(3, 2), dpi=80)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.15)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.data = deque(maxlen=50)

    def add_point(self, val):
        self.data.append(val)
        self._draw()

    def _draw(self):
        self.ax.clear()
        self.ax.plot(self.data, color='#e74c3c')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_title(self.type_var.get(), fontsize=8)
        self.canvas.draw()