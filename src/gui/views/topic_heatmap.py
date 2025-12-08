import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np


class TopicHeatmap(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.fig = Figure(figsize=(5, 3), dpi=80) # Lower DPI to fit sidebar
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(bottom=0.25, left=0.35, right=0.95, top=0.9) # Adjust margins

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_plot(self, topic_counts):
        self.ax.clear()

        # Handle Empty State
        if not topic_counts:
            self.ax.text(0.5, 0.5, "Waiting for Traffic...",
                         ha='center', va='center', transform=self.ax.transAxes, color='#95a5a6')
            self.ax.set_xticks([])
            self.ax.set_yticks([])
            self.canvas.draw()
            return

        topics = list(topic_counts.keys())
        counts = list(topic_counts.values())
        y_pos = np.arange(len(topics))

        bars = self.ax.barh(y_pos, counts, align='center', alpha=0.8)

        # Color based on volume
        max_val = max(counts) if max(counts) > 0 else 1
        for bar, count in zip(bars, counts):
            # Blue -> Purple gradient
            bar.set_color((count/max_val * 0.5, 0.2, 0.8))

        self.ax.set_yticks(y_pos)
        self.ax.set_yticklabels(topics, fontsize=8)
        self.ax.invert_yaxis()
        self.ax.set_xlabel('Msg / Sec', fontsize=8)
        self.ax.tick_params(axis='x', labelsize=8)
        self.ax.grid(axis='x', linestyle='--', alpha=0.3)

        self.canvas.draw()