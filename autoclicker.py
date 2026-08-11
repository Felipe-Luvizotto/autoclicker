#!/usr/bin/env python3
"""
AutoClicker - clone do GS Auto Clicker para Linux (Wayland/X11).

- UI em Tkinter: intervalo (ms) e tecla de atalho configuraveis.
- Tecla de atalho global (funciona mesmo com outra janela em foco) via
  leitura direta do dispositivo de teclado (python-evdev).
- Clique simulado via ydotool (funciona em Wayland e X11), atraves do
  daemon ydotoold.

Requisitos de sistema (uma vez so): rode ./install.sh (ver README.md).
"""

import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from evdev import InputDevice, categorize, ecodes, list_devices
except ImportError:
    InputDevice = None
    ecodes = None
    list_devices = None

DRAG_POLL_MS = 10

YDOTOOL_LEFT_CLICK = ["ydotool", "click", "0xC0"]

# Mapa de teclas comuns (nome exibido -> codigo evdev)
KEY_NAME_TO_CODE = {}
if ecodes is not None:
    for _name in dir(ecodes):
        if _name.startswith("KEY_"):
            KEY_NAME_TO_CODE[_name[4:]] = getattr(ecodes, _name)


def find_keyboards():
    """Retorna a lista de dispositivos evdev que parecem teclados."""
    devices = []
    if list_devices is None:
        return devices
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except (OSError, PermissionError):
            continue
        if "ydotool" in dev.name.lower():
            # Dispositivo virtual criado pelo proprio ydotoold: ignora,
            # senao o programa "escuta" os cliques que ele mesmo gera.
            dev.close()
            continue
        caps = dev.capabilities().get(ecodes.EV_KEY, [])
        # Teclado tem varias teclas de letras; filtra mouses/outros.
        if ecodes.KEY_A in caps and ecodes.KEY_Z in caps:
            devices.append(dev)
        else:
            dev.close()
    return devices


TITLEBAR_BG = "#2b2b2b"
TITLEBAR_FG = "#ffffff"


class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoClicker")
        self.root.resizable(False, False)
        # Sem barra de titulo nativa neste compositor (Hyprland/XWayland);
        # a barra customizada abaixo cobre essa funcao.
        self.root.configure(bg=TITLEBAR_BG)

        # Arrastar a janela: consultar a posicao do cursor via X11
        # (event.x_root ou winfo_pointerx/y) enquanto a PROPRIA janela
        # esta sendo reposicionada via geometry() da leituras cada vez
        # mais erradas no XWayland/Hyprland (loop de realimentacao
        # confirmado em teste isolado -- por isso o "teleporte"). A
        # posicao do cursor e obtida via "hyprctl cursorpos" em vez
        # disso, que consulta o estado interno do compositor direto,
        # sem passar pela traducao de coordenadas dessa janela.
        self._dragging = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0

        self.clicking = False
        self.click_thread = None
        self.stop_event = threading.Event()

        self.hotkey_name = tk.StringVar(value="F6")
        self.capturing_hotkey = False

        self.interval_ms = tk.StringVar(value="100")
        self.status_var = tk.StringVar(value="Parado")

        self._build_ui()

        self.listener_thread = None
        self.listener_stop = threading.Event()
        self._start_hotkey_listener()

    # ---------------- UI ----------------

    def _build_ui(self):
        self._build_title_bar()

        pad = {"padx": 10, "pady": 6}
        frame = ttk.Frame(self.root)
        frame.pack(side="top", fill="both", expand=True)

        ttk.Label(frame, text="Intervalo entre cliques (ms):").grid(
            row=0, column=0, sticky="w", **pad
        )
        interval_entry = ttk.Entry(frame, textvariable=self.interval_ms, width=10)
        interval_entry.grid(row=0, column=1, sticky="w", **pad)

        ttk.Label(frame, text="Tecla de atalho (start/stop):").grid(
            row=1, column=0, sticky="w", **pad
        )
        self.hotkey_btn = ttk.Button(
            frame, textvariable=self.hotkey_name, width=10, command=self._capture_hotkey
        )
        self.hotkey_btn.grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(frame, text="(clique e aperte uma tecla)").grid(
            row=1, column=2, sticky="w", **pad
        )

        self.toggle_btn = ttk.Button(frame, text="Iniciar (F6)", command=self.toggle_clicking)
        self.toggle_btn.grid(row=2, column=0, columnspan=2, sticky="we", **pad)

        ttk.Label(frame, text="Status:").grid(row=3, column=0, sticky="w", **pad)
        self.status_label = ttk.Label(frame, textvariable=self.status_var, foreground="red")
        self.status_label.grid(row=3, column=1, sticky="w", **pad)

        if InputDevice is None:
            ttk.Label(
                frame,
                text="Aviso: python-evdev nao encontrado.\nTecla de atalho global desativada.",
                foreground="orange",
            ).grid(row=4, column=0, columnspan=3, sticky="w", **pad)

    def _build_title_bar(self):
        bar = tk.Frame(self.root, bg=TITLEBAR_BG, height=30)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        title_label = tk.Label(
            bar, text="AutoClicker", bg=TITLEBAR_BG, fg=TITLEBAR_FG, font=("Segoe UI", 10)
        )
        title_label.pack(side="left", padx=10)

        close_btn = tk.Label(
            bar, text="✕", bg=TITLEBAR_BG, fg=TITLEBAR_FG, font=("Segoe UI", 11), width=3
        )
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Button-1>", lambda e: self.on_close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#e81123"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=TITLEBAR_BG))

        min_btn = tk.Label(
            bar, text="—", bg=TITLEBAR_BG, fg=TITLEBAR_FG, font=("Segoe UI", 11), width=3
        )
        min_btn.pack(side="right", fill="y")
        min_btn.bind("<Button-1>", lambda e: self.root.iconify())
        min_btn.bind("<Enter>", lambda e: min_btn.config(bg="#3f3f3f"))
        min_btn.bind("<Leave>", lambda e: min_btn.config(bg=TITLEBAR_BG))

        # Arrastar a janela segurando a barra (como uma titlebar normal).
        for widget in (bar, title_label):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<ButtonRelease-1>", self._stop_drag)

    def _get_cursor_pos(self):
        """Posicao global do cursor via hyprctl (estado do compositor),
        em vez de consultas X11 (event.x_root / winfo_pointerx), que
        ficam erradas enquanto esta mesma janela e reposicionada."""
        try:
            result = subprocess.run(
                ["hyprctl", "cursorpos"], capture_output=True, text=True, timeout=0.3
            )
            x_str, y_str = result.stdout.strip().split(",")
            return int(x_str.strip()), int(y_str.strip())
        except Exception:
            return self.root.winfo_pointerx(), self.root.winfo_pointery()

    def _start_drag(self, _event):
        cur_x, cur_y = self._get_cursor_pos()
        self._drag_offset_x = cur_x - self.root.winfo_x()
        self._drag_offset_y = cur_y - self.root.winfo_y()
        self._dragging = True
        self._drag_poll()

    def _stop_drag(self, _event):
        self._dragging = False

    def _drag_poll(self):
        if not self._dragging:
            return
        cur_x, cur_y = self._get_cursor_pos()
        x = cur_x - self._drag_offset_x
        y = cur_y - self._drag_offset_y
        self.root.geometry(f"+{x}+{y}")
        self.root.after(DRAG_POLL_MS, self._drag_poll)

    def _capture_hotkey(self):
        if InputDevice is None:
            messagebox.showerror("Erro", "python-evdev nao esta instalado.")
            return
        self.capturing_hotkey = True
        self.hotkey_name.set("...")
        self.hotkey_btn.state(["disabled"])

    # ---------------- Hotkey listener (evdev, global) ----------------

    def _start_hotkey_listener(self):
        if InputDevice is None:
            return
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()

    def _listen_loop(self):
        devices = find_keyboards()
        if not devices:
            self._set_status_threadsafe("Sem acesso ao teclado (grupo 'input'?)")
            return

        import selectors

        sel = selectors.DefaultSelector()
        for dev in devices:
            sel.register(dev, selectors.EVENT_READ)

        try:
            while not self.listener_stop.is_set():
                for key, _ in sel.select(timeout=0.5):
                    dev = key.fileobj
                    try:
                        for event in dev.read():
                            if event.type != ecodes.EV_KEY:
                                continue
                            if event.value != 1:  # somente key-down
                                continue
                            key_event = categorize(event)
                            self._on_key_event(key_event.keycode)
                    except (OSError, BlockingIOError):
                        continue
        finally:
            for dev in devices:
                try:
                    dev.close()
                except OSError:
                    pass

    def _on_key_event(self, keycode):
        # keycode pode ser string ("KEY_F6") ou lista de strings
        if isinstance(keycode, list):
            names = [k[4:] for k in keycode]
        else:
            names = [keycode[4:]]

        if self.capturing_hotkey:
            self.hotkey_name.set(names[0])
            self.capturing_hotkey = False
            self.root.after(0, lambda: self.hotkey_btn.state(["!disabled"]))
            self.root.after(0, self._update_toggle_label)
            return

        if self.hotkey_name.get() in names:
            self.root.after(0, self.toggle_clicking)

    def _update_toggle_label(self):
        action = "Parar" if self.clicking else "Iniciar"
        self.toggle_btn.config(text=f"{action} ({self.hotkey_name.get()})")

    def _set_status_threadsafe(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    # ---------------- Clicking ----------------

    def toggle_clicking(self):
        if self.clicking:
            self._stop_clicking()
        else:
            self._start_clicking()

    def _start_clicking(self):
        try:
            interval = max(1, int(self.interval_ms.get()))
        except ValueError:
            messagebox.showerror("Erro", "Intervalo invalido. Use um numero em ms.")
            return

        self.clicking = True
        self.stop_event.clear()
        self.status_var.set("Clicando...")
        self.status_label.config(foreground="green")
        self._update_toggle_label()

        self.click_thread = threading.Thread(
            target=self._click_loop, args=(interval,), daemon=True
        )
        self.click_thread.start()

    def _stop_clicking(self):
        self.clicking = False
        self.stop_event.set()
        self.status_var.set("Parado")
        self.status_label.config(foreground="red")
        self._update_toggle_label()

    def _click_loop(self, interval_ms):
        delay = interval_ms / 1000.0
        while not self.stop_event.is_set():
            try:
                subprocess.run(YDOTOOL_LEFT_CLICK, check=False, capture_output=True)
            except FileNotFoundError:
                self._set_status_threadsafe("Erro: ydotool nao encontrado")
                self.clicking = False
                return
            time.sleep(delay)

    def on_close(self):
        self.listener_stop.set()
        self.stop_event.set()
        self._dragging = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AutoClickerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
