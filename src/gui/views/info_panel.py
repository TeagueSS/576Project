import tkinter as tk
from tkinter import ttk


class InfoPanel(ttk.Frame):
    def __init__(self, parent, on_save_settings):
        super().__init__(parent, style="Card.TFrame", padding=15)
        self.on_save = on_save_settings
        self.current_node = None

        ttk.Label(self, text="Node Properties", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))

        self.content_area = ttk.Frame(self, style="Card.TFrame")
        self.content_area.pack(fill=tk.BOTH, expand=True)

        self.show_general_info("Select a node on the map to edit.")

    def _clear(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def show_general_info(self, text):
        self._clear()
        lbl = tk.Label(self.content_area, text=text, bg="#FFFFFF", fg="#95a5a6", wraplength=250, justify="left",
                       font=("Segoe UI", 10, "italic"))
        lbl.pack(anchor="nw", pady=10)

    def show_node_details(self, node_data):
        self._clear()
        self.current_node = node_data

        form = tk.Frame(self.content_area, bg="#FFFFFF")
        form.pack(fill="x")

        # ID
        tk.Label(form, text=node_data['id'], font=("Segoe UI", 12, "bold"), fg="#2c3e50", bg="#FFFFFF").pack(anchor="w",
                                                                                                             pady=(
                                                                                                             0, 5))
        tk.Label(form, text="Device Configuration", font=("Segoe UI", 8, "bold"), fg="#95a5a6", bg="#FFFFFF").pack(
            anchor="w", pady=(0, 10))

        # 1. Type
        type_var = tk.StringVar(value=node_data.get('type', 'Sensor'))
        cb_type = ttk.Combobox(form, textvariable=type_var,
                               values=["Gateway", "Sensor", "iPhone", "Laptop", "Asset Tag", "Beacon"],
                               state="readonly")
        cb_type.pack(fill="x", pady=(0, 10))

        # 2. State
        state_var = tk.StringVar(value=node_data.get('state', 'active'))
        cb_state = ttk.Combobox(form, textvariable=state_var, values=["active", "scanning", "disconnected", "dead"],
                                state="readonly")
        cb_state.pack(fill="x", pady=(0, 10))

        # 3. RANGE Slider
        current_range = node_data.get('range', 50)
        range_frame = tk.Frame(form, bg="#FFFFFF")
        range_frame.pack(fill="x")
        tk.Label(range_frame, text="Transmit Range", font=("Segoe UI", 9), bg="#FFFFFF").pack(side=tk.LEFT)
        lbl_range = tk.Label(range_frame, text=f"{int(current_range)} m", font=("Segoe UI", 9, "bold"), fg="#3498db",
                             bg="#FFFFFF")
        lbl_range.pack(side=tk.RIGHT)

        range_var = tk.DoubleVar(value=current_range)

        def on_slide(val):
            lbl_range.config(text=f"{int(float(val))} m")
            do_save()

        scale = ttk.Scale(form, from_=10, to=400, variable=range_var, orient="horizontal", command=on_slide)
        scale.pack(fill="x", pady=(0, 10))

        def do_save(*args):
            changes = {
                'type': type_var.get(),
                'state': state_var.get(),
                'range': range_var.get()
            }
            self.on_save(node_data['id'], changes)

        cb_type.bind("<<ComboboxSelected>>", do_save)
        cb_state.bind("<<ComboboxSelected>>", do_save)