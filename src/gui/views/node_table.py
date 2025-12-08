import tkinter as tk
from tkinter import ttk

class NodeTable(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame", padding=15)

        # Header
        ttk.Label(self, text="Node Status List", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))

        # Define columns
        columns = ("id", "type", "state", "battery", "retries", "wait")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10, selectmode="browse")

        # Configure Column Headings
        self.tree.heading("id", text="ID")
        self.tree.heading("type", text="Type")
        self.tree.heading("state", text="State")
        self.tree.heading("battery", text="Batt")
        self.tree.heading("retries", text="Retries")
        self.tree.heading("wait", text="Wait (s)")

        # Configure Column Widths (Adjust as needed)
        self.tree.column("id", width=60, anchor="w")
        self.tree.column("type", width=70, anchor="w")
        self.tree.column("state", width=70, anchor="center")
        self.tree.column("battery", width=40, anchor="e")
        self.tree.column("retries", width=50, anchor="center")
        self.tree.column("wait", width=50, anchor="e")

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        # Layout
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Style tweaking for rows (optional tags)
        self.tree.tag_configure("active", foreground="#27ae60")       # Green
        self.tree.tag_configure("dead", foreground="#c0392b")         # Red
        self.tree.tag_configure("scanning", foreground="#e67e22")     # Orange
        self.tree.tag_configure("disconnected", foreground="#7f8c8d") # Gray

    def update_table(self, nodes_data):
        # 1. Capture current selection to restore it after refresh
        selected_item = self.tree.selection()
        selected_id = self.tree.item(selected_item[0])['values'][0] if selected_item else None

        # 2. Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 3. Insert new data
        for n in nodes_data:
            # Determine visual tag based on state
            tag = "active"
            if n['state'] == "dead": tag = "dead"
            elif n['state'] == "scanning": tag = "scanning"
            elif n['state'] == "disconnected": tag = "disconnected"

            retry_txt = str(n.get('retries', 0)) if n.get('retries', 0) > 0 else "-"
            wait_txt = f"{n.get('next_retry', 0):.1f}s" if n.get('retries', 0) > 0 else "-"

            self.tree.insert("", tk.END, values=(
                n['id'],
                n['type'],
                n['state'].capitalize(),
                f"{n['battery']}%",
                retry_txt,
                wait_txt
            ), tags=(tag,))

        # 4. Restore selection if the node still exists
        if selected_id:
            for item in self.tree.get_children():
                if self.tree.item(item)['values'][0] == selected_id:
                    self.tree.selection_set(item)
                    self.tree.see(item)
                    break