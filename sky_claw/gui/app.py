import asyncio
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import sv_ttk

logger = logging.getLogger(__name__)

class SkyClawGUI:
    """Modern Desktop GUI for Sky-Claw."""
    
    def __init__(self, ctx):
        self.ctx = ctx
        self.root = tk.Tk()
        self.root.title("Sky-Claw: Skyrim Modding Agent")
        self.root.geometry("1000x700")
        
        sv_ttk.set_theme("dark")
        
        self._setup_ui()
        self.msg_queue = queue.Queue()
        self._start_logic_thread()
        self._poll_queue()

    def _setup_ui(self):
        # Main Paned Window
        self.paned = ttk.PanedWindow(self.root, orient="horizontal")
        self.paned.pack(fill="both", expand=True)
        
        # Left Panel: Mod List
        self.left_frame = ttk.Frame(self.paned)
        self.paned.add(self.left_frame, weight=1)
        
        ttk.Label(self.left_frame, text="Active Mods", font=("Segoe UI", 12, "bold")).pack(pady=5)
        
        self.mod_tree = ttk.Treeview(self.left_frame, columns=("Index", "Name"), show="headings")
        self.mod_tree.heading("Index", text="#")
        self.mod_tree.heading("Name", text="Mod Name")
        self.mod_tree.column("Index", width=50, stretch=False)
        self.mod_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Right Panel: Chat Console
        self.right_frame = ttk.Frame(self.paned)
        self.paned.add(self.right_frame, weight=2)
        
        ttk.Label(self.right_frame, text="Agent Console", font=("Segoe UI", 12, "bold")).pack(pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(self.right_frame, wrap="word", state="disabled", font=("Consolas", 10))
        self.chat_display.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.input_frame = ttk.Frame(self.right_frame)
        self.input_frame.pack(fill="x", padx=5, pady=10)
        
        self.input_var = tk.StringVar()
        self.entry = ttk.Entry(self.input_frame, textvariable=self.input_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = ttk.Button(self.input_frame, text="Send", command=self._send_message)
        self.send_btn.pack(side="right")

    def _send_message(self):
        text = self.input_var.get().strip()
        if not text:
            return
        
        self._append_chat(f"You: {text}\n")
        self.input_var.set("")
        
        # Dispatch to logic thread
        self.msg_queue.put(("chat", text))

    def _append_chat(self, text):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", text)
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self.ctx.gui_queue.get_nowait()
                if msg_type == "response":
                    self._append_chat(f"Sky-Claw: {data}\n\n")
                elif msg_type == "modlist":
                    self._update_mod_list(data)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _update_mod_list(self, mods):
        self.mod_tree.delete(*self.mod_tree.get_children())
        for i, mod in enumerate(mods, 1):
            self.mod_tree.insert("", "end", values=(i, mod))

    def _start_logic_thread(self):
        # This will be handled in __main__.py by integrating with ctx
        pass

    def run(self):
        self.root.mainloop()
