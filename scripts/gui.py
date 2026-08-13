import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import sys

# ── Paleta ────────────────────────────────────────────────────────────────────
BG       = "#1a1a2e"
SURFACE  = "#16213e"
CARD     = "#0f3460"
ACCENT   = "#e94560"
SUCCESS  = "#4ecca3"
WARNING  = "#f5a623"
FG       = "#eaeaea"
FG_DIM   = "#8892a4"


# ── Redirecionamento de stdout para a GUI ─────────────────────────────────────
class _StdoutRedirect:
    def __init__(self, q: queue.Queue):
        self._q = q

    def write(self, text):
        if text.strip():
            self._q.put(("log", text.rstrip()))

    def flush(self):
        pass


# ── Janela de confirmação de upload ───────────────────────────────────────────
class UploadConfirmDialog(tk.Toplevel):
    def __init__(self, parent, monitorado: str, arquivo: str, destino: str):
        super().__init__(parent)
        self.result = False
        self.title("Confirmar Upload")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        pad = dict(padx=20, pady=8)

        tk.Label(self, text="Confirmar Upload", bg=BG, fg=FG,
                 font=("Segoe UI", 13, "bold")).pack(**pad, pady=(20, 4))

        frame = tk.Frame(self, bg=SURFACE)
        frame.pack(padx=20, pady=8, fill="x")

        for label, value in [("Monitorado", monitorado), ("Arquivo", arquivo), ("Destino", destino)]:
            row = tk.Frame(frame, bg=SURFACE)
            row.pack(fill="x", padx=12, pady=4)
            tk.Label(row, text=f"{label}:", bg=SURFACE, fg=FG_DIM,
                     font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=SURFACE, fg=FG,
                     font=("Segoe UI", 9, "bold"), anchor="w",
                     wraplength=380, justify="left").pack(side="left", fill="x", expand=True)

        tk.Label(self, text="✓  Arquivo pronto para ser anexado.",
                 bg=BG, fg=SUCCESS, font=("Segoe UI", 9, "italic")).pack(**pad)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(4, 20))

        tk.Button(btn_frame, text="CONFIRMAR UPLOAD", bg=SUCCESS, fg="#0a0a0a",
                  font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                  padx=18, pady=8, command=self._confirm).pack(side="left", padx=8)

        tk.Button(btn_frame, text="CANCELAR", bg=ACCENT, fg=FG,
                  font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                  padx=18, pady=8, command=self._cancel).pack(side="left", padx=8)

        self.protocol("WM_DELETE_WINDOW", self._cancel)

        # Força a janela para frente, mesmo com o Chrome em foco
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()

        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")
        self.wait_window()

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


# ── Janela principal ───────────────────────────────────────────────────────────
class CEMEPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CEMEP — Automatização")
        self.configure(bg=BG)
        self.geometry("780x560")
        self.minsize(680, 480)

        self._msg_queue: queue.Queue = queue.Queue()
        self._running = False

        sys.stdout = _StdoutRedirect(self._msg_queue)

        self._build_ui()
        self._poll()

    def _build_ui(self):
        # Cabeçalho
        header = tk.Frame(self, bg=CARD, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="CEMEP — Automatização",
                 bg=CARD, fg=FG, font=("Segoe UI", 16, "bold")).pack()
        tk.Label(header, text="Automação de documentos e integração com o Chronos",
                 bg=CARD, fg=FG_DIM, font=("Segoe UI", 9)).pack()

        # Botões
        btn_frame = tk.Frame(self, bg=BG, pady=18)
        btn_frame.pack(fill="x", padx=32)

        self._btn_scan = self._make_btn(btn_frame, "⬡  EXECUTAR SCAN", ACCENT, self._run_scan)
        self._btn_scan.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self._btn_manual = self._make_btn(btn_frame, "⬡  EXECUTAR MANUAL", CARD, self._run_manual)
        self._btn_manual.pack(side="left", expand=True, fill="x", padx=(10, 0))

        # Status
        self._status_var = tk.StringVar(value="Aguardando.")
        sf = tk.Frame(self, bg=SURFACE, pady=6)
        sf.pack(fill="x", padx=32)
        tk.Label(sf, textvariable=self._status_var, bg=SURFACE, fg=FG_DIM,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=10)

        # Log
        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=32, pady=(8, 4))
        tk.Label(log_frame, text="LOG DE EXECUÇÃO", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 4))

        self._log = scrolledtext.ScrolledText(
            log_frame, bg=SURFACE, fg=FG, font=("Consolas", 9),
            relief="flat", state="disabled", wrap="word",
            insertbackground=FG, bd=0, highlightthickness=0,
        )
        self._log.pack(fill="both", expand=True)
        self._log.tag_config("ok",    foreground=SUCCESS)
        self._log.tag_config("erro",  foreground=ACCENT)
        self._log.tag_config("aviso", foreground=WARNING)
        self._log.tag_config("info",  foreground=FG)
        self._log.tag_config("dim",   foreground=FG_DIM)

        tk.Label(self, text="SEJUC — Sergipe  •  ChronosFlow",
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 8)).pack(pady=(2, 8))

    def _make_btn(self, parent, text, color, command):
        return tk.Button(
            parent, text=text, bg=color, fg=FG,
            font=("Segoe UI", 11, "bold"), relief="flat",
            cursor="hand2", padx=0, pady=14,
            activebackground=color, activeforeground=FG,
            command=command,
        )

    def _set_busy(self, label: str):
        self._running = True
        self._btn_scan.config(state="disabled",   text="⏳  PROCESSANDO...")
        self._btn_manual.config(state="disabled", text="⏳  PROCESSANDO...")
        self._status_var.set(f"Executando: {label}")

    def _set_idle(self):
        self._running = False
        self._btn_scan.config(state="normal",   text="⬡  EXECUTAR SCAN")
        self._btn_manual.config(state="normal", text="⬡  EXECUTAR MANUAL")
        self._status_var.set("Aguardando.")

    def _append_log(self, text: str, tag: str = "info"):
        self._log.config(state="normal")
        self._log.insert("end", text + "\n", tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _tag_for(self, text: str) -> str:
        tl = text.lower()
        if any(k in tl for k in ("erro", "error", "falha", "não encontrad")):
            return "erro"
        if any(k in tl for k in ("concluí", "sucesso", "movido", "ok", "✓")):
            return "ok"
        if any(k in tl for k in ("tentativa", "↻", "aguard", "aviso")):
            return "aviso"
        if text.startswith(("─", "=", "==")):
            return "dim"
        return "info"

    def _poll(self):
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload, self._tag_for(payload))
                elif kind == "done":
                    self._set_idle()
                    self._append_log("─" * 52, "dim")
                    self._append_log("Processamento finalizado.", "ok")
                elif kind == "confirm":
                    monitorado, arquivo, destino, event, holder = payload
                    # Traz a janela principal para frente antes de abrir o diálogo
                    self.attributes("-topmost", True)
                    self.lift()
                    self.focus_force()
                    self.after(100, lambda: self.attributes("-topmost", False))
                    dlg = UploadConfirmDialog(self, monitorado, arquivo, destino)
                    holder["result"] = dlg.result
                    event.set()
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _run_scan(self):
        if self._running:
            return
        self._set_busy("SCAN")
        self._append_log("─" * 52, "dim")
        self._append_log("Iniciando fluxo SCAN...", "info")
        threading.Thread(target=self._worker, args=("scan",), daemon=True).start()

    def _run_manual(self):
        if self._running:
            return
        self._set_busy("MANUAL")
        self._append_log("─" * 52, "dim")
        self._append_log("Iniciando fluxo MANUAL...", "info")
        threading.Thread(target=self._worker, args=("manual",), daemon=True).start()

    def _worker(self, modo: str):
        try:
            import main as m
            logger = m.setup_logging()
            driver, wait = m.chronos_login()
            if modo == "scan":
                fila = m.processar_scan(driver, wait, logger, self._msg_queue)
            else:
                fila = m.processar_manual(driver, wait, logger, self._msg_queue)
            m.print_summary(fila)
            driver.quit()
        except Exception as e:
            self._msg_queue.put(("log", f"ERRO fatal: {e}"))
        finally:
            self._msg_queue.put(("done", None))


if __name__ == "__main__":
    CEMEPApp().mainloop()