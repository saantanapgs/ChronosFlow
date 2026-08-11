import tkinter as tk

def execute_scan():
    # Lógica para executar a digitalização
    print("Scan inicializado...")

window = tk.Tk()
window.title("ChronosFlow")
window.geometry("800x500")

title = tk.Label(
    window,
    text="ChronosFlow",
)
title.pack()

btn_scan = tk.Button(
    window, 
    text="Iniciar Scan",
    command=execute_scan
)
btn_scan.pack()

window.mainloop()