import tkinter as tk
from tkinter import ttk


class InfoPanel(ttk.LabelFrame):
    def __init__(self, parent, on_save_settings):
        super().__init__(parent, text="Details")
        self.on_save = on_save_settings
        self.current_node = None

        self.content_area = ttk.Frame(self)
        self.content_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.show_general_info("Welcome.\n\nDrag nodes to move them.\nClick a node to edit properties.")

    def _clear(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def show_general_info(self, text):
        self._clear()
        lbl = tk.Label(self.content_area, text=text, wraplength=200, justify="left")
        lbl.pack(anchor="nw", pady=10)

    def show_node_details(self, node_data):
        self._clear()
        self.current_node = node_data

        # Header
        header = ttk.Frame(self.content_area)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="ID:", font="bold").pack(side=tk.LEFT)
        ttk.Label(header, text=node_data['id'], foreground="blue").pack(side=tk.LEFT, padx=5)

        # 1. Node Type
        ttk.Label(self.content_area, text="Node Type:").pack(anchor="w")
        type_var = tk.StringVar(value=node_data.get('type', 'Sensor'))
        ttk.Combobox(self.content_area, textvariable=type_var,
                     values=["Gateway", "Sensor", "iPhone", "Laptop"]).pack(fill="x", pady=(0, 5))

        # 2. IP Address
        ttk.Label(self.content_area, text="IP Address:").pack(anchor="w")
        ip_var = tk.StringVar(value=node_data.get('ip', '0.0.0.0'))
        ttk.Entry(self.content_area, textvariable=ip_var).pack(fill="x", pady=(0, 5))

        # 3. State
        ttk.Label(self.content_area, text="State:").pack(anchor="w")
        state_var = tk.StringVar(value=node_data.get('state', 'active'))
        ttk.Combobox(self.content_area, textvariable=state_var,
                     values=["active", "sleep", "dead", "booting"]).pack(fill="x", pady=(0, 5))

        # 4. Strength
        ttk.Label(self.content_area, text="Tx Power (dBm):").pack(anchor="w")
        strength_var = tk.DoubleVar(value=node_data.get('strength', 10.0))
        ttk.Scale(self.content_area, from_=-30, to=20, variable=strength_var, orient="horizontal").pack(fill="x")
        lbl_strength = ttk.Label(self.content_area, text=f"{strength_var.get()} dBm")
        lbl_strength.pack(anchor="e")
        strength_var.trace("w", lambda *args: lbl_strength.config(text=f"{strength_var.get():.1f} dBm"))

        # 5. Battery
        ttk.Label(self.content_area, text="Battery (%):").pack(anchor="w")
        batt_var = tk.IntVar(value=node_data.get('battery', 100))
        ttk.Scale(self.content_area, from_=0, to=100, variable=batt_var, orient="horizontal").pack(fill="x")
        lbl_batt = ttk.Label(self.content_area, text=f"{batt_var.get()}%")
        lbl_batt.pack(anchor="e", pady=(0, 10))
        batt_var.trace("w", lambda *args: lbl_batt.config(text=f"{batt_var.get()}%"))

        def do_save():
            changes = {
                'type': type_var.get(),
                'ip': ip_var.get(),
                'state': state_var.get(),
                'strength': strength_var.get(),
                'battery': batt_var.get()
            }
            self.on_save(node_data['id'], changes)

        ttk.Button(self.content_area, text="💾 Apply Changes", command=do_save).pack(fill="x", pady=10)

    def show_logs(self, logs):
        self._clear()
        ttk.Label(self.content_area, text="Runtime Logs", font="bold").pack(anchor="w")
        log_box = tk.Text(self.content_area, height=20, width=30, font=("Courier", 9))
        log_box.pack(fill="both", expand=True)
        for l in logs:
            log_box.insert(tk.END, f"> {l}\n")