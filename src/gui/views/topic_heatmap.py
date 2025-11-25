"""Heatmap visualizing per-topic message throughput."""
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np


class TopicHeatmap(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(bottom=0.3, left=0.2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_plot(self, topic_counts):
        """
        topic_counts: dict { 'topic_name': count }
        """
        self.ax.clear()

        topics = list(topic_counts.keys())
        counts = list(topic_counts.values())

        if not topics:
            self.canvas.draw()
            return

        y_pos = np.arange(len(topics))

        # Horizontal Bar Chart (serving as a "heatmap" for topic intensity)
        # Using a colormap to indicate intensity
        bars = self.ax.barh(y_pos, counts, align='center', alpha=0.7)

        # Color bars based on value
        max_val = max(counts) if counts and max(counts) > 0 else 1
        for bar, count in zip(bars, counts):
            bar.set_color(self._get_color(count, max_val))

        self.ax.set_yticks(y_pos)
        self.ax.set_yticklabels(topics)
        self.ax.invert_yaxis()  # labels read top-to-bottom
        self.ax.set_xlabel('Messages Processed')
        self.ax.grid(axis='x', linestyle='--', alpha=0.5)

        self.canvas.draw()

    def _get_color(self, value, max_val):
        """Returns a color ranging from blue (low) to red (high)."""
        # Simple R-B interpolation
        ratio = value / max_val
        return (ratio, 0, 1 - ratio)  # RGB