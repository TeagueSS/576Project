import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class QueueSparkline(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.fig = Figure(figsize=(5, 2), dpi=80)
        self.ax = self.fig.add_subplot(111)
        # Tight layout for sparkline feel
        self.fig.subplots_adjust(bottom=0.15, top=0.9, left=0.1, right=0.95)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_plot(self, queue_history):
        self.ax.clear()

        # Ensure we have data to plot
        if not queue_history:
            queue_history = [0] * 50

        x_data = range(len(queue_history))
        self.ax.plot(x_data, queue_history, color='#e74c3c', linewidth=1.5)
        self.ax.fill_between(x_data, queue_history, color='#e74c3c', alpha=0.1)

        # Force Y-limit so a flatline at 0 looks intentional (at bottom) not middle
        current_max = max(queue_history) if queue_history else 0
        self.ax.set_ylim(0, max(5, current_max * 1.2))

        self.ax.grid(True, linestyle=':', alpha=0.5)
        self.ax.set_ylabel("Depth", fontsize=8)
        self.ax.set_xticks([]) # Hide X axis time
        self.ax.tick_params(axis='y', labelsize=8)

        self.canvas.draw()