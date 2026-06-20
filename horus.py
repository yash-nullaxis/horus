import os
os.environ['SYSTEM_VERSION_COMPAT'] = '1'

import tkinter as tk
from tkinter import filedialog, scrolledtext
import subprocess
import time
import threading
import queue
import sys

def enqueue_output(out, q):
    try:
        for line in iter(out.readline, ''):
            if line:
                q.put(line)
    except ValueError:
        pass
    out.close()

def run_tests_thread(folder_path, q_ui):
    q_ui.put(f"Starting OpenWork orchestrator on {folder_path}...\n")

    # We must use the submodule, not the global CLI.
    # The submodule is in "openwork/apps/orchestrator". However, the openwork orchestrator
    # binary is compiled or run via npm/bun/pnpm. The easiest way to run the local submodule
    # is using its start command or the built cli.js.
    # According to the README, we can run it via source using pnpm.
    # Command: pnpm --filter openwork-orchestrator dev -- start --workspace <folder> --approval auto

    # Path to the submodule
    submodule_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "openwork"))

    openwork_proc = subprocess.Popen(
        ["pnpm", "--filter", "openwork-orchestrator", "dev", "--", "serve", "--workspace", folder_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=submodule_path
    )

    # Give the server a moment to boot
    time.sleep(10)

    q_ui.put("OpenWork server started. Triggering AI to generate E2E tests...\n")

    # Run the JS bridge script
    js_script_path = os.path.abspath("generate_tests.mjs")

    bridge_proc = subprocess.Popen(
        ["node", js_script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in bridge_proc.stdout:
        q_ui.put(f"AI: {line}")

    bridge_proc.wait()

    q_ui.put("\nAI finished generating tests. Now we will run the tests...\n")

    # Terminate the openwork server
    openwork_proc.terminate()
    try:
        openwork_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        openwork_proc.kill()

    # Check for test runner
    test_command = []
    if os.path.exists(os.path.join(folder_path, "package.json")):
        q_ui.put("Found package.json. Running Playwright via npx...\n")
        test_command = ["npx", "playwright", "test"]
    elif os.path.exists(os.path.join(folder_path, "requirements.txt")) or os.path.exists(os.path.join(folder_path, "pytest.ini")):
        q_ui.put("Found Python requirements. Running Playwright via pytest...\n")
        test_command = ["pytest"]
    else:
        q_ui.put("Could not determine test runner automatically. Trying npx playwright test as fallback...\n")
        test_command = ["npx", "playwright", "test"]

    test_proc = subprocess.Popen(
        test_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=folder_path
    )

    for line in test_proc.stdout:
        q_ui.put(line)

    test_proc.wait()

    if test_proc.returncode == 0:
        q_ui.put("\n✅ Tests passed successfully!\n")
    else:
        q_ui.put(f"\n❌ Tests failed with code {test_proc.returncode}.\n")

class HorusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Horus")
        self.root.geometry("600x400")

        self.btn = tk.Button(self.root, text="Select Folder & Generate/Run Tests", command=self.select_folder)
        self.btn.pack(pady=10)

        self.lbl_folder = tk.Label(self.root, text="No folder selected", fg="blue")
        self.lbl_folder.pack(pady=5)

        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=70, height=18)
        self.text_area.pack(pady=10)

        self.ui_queue = queue.Queue()
        self.process_queue()

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.lbl_folder.config(text=f"Selected: {folder_path}")
            self.text_area.delete(1.0, tk.END)
            threading.Thread(target=run_tests_thread, args=(folder_path, self.ui_queue), daemon=True).start()

    def process_queue(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                self.text_area.insert(tk.END, msg)
                self.text_area.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = HorusApp(root)
    root.mainloop()
