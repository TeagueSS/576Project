"""Sparkline showing broker queue depth over time."""
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class QueueSparkline(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.fig = Figure(figsize=(5, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(bottom=0.2, top=0.9, left=0.1, right=0.95)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_plot(self, queue_history):
        """
        queue_history: list of integers (queue depth over time)
        """
        self.ax.clear()

        if not queue_history:
            self.canvas.draw()
            return

        self.ax.plot(queue_history, color='#007acc', linewidth=1.5)
        self.ax.fill_between(range(len(queue_history)), queue_history, color='#007acc', alpha=0.2)

        self.ax.set_ylim(bottom=0)
        self.ax.grid(True, linestyle=':', alpha=0.5)
        self.ax.set_ylabel("Depth")

        # Remove X ticks for cleaner "sparkline" look
        self.ax.set_xticks([])

        self.canvas.draw()