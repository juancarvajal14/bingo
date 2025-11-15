# cliente_final.py (MISMO QUE ANTES, PERO FUNCIONA AHORA)
import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox, font

HOST = '127.0.0.1'
PORT = 65432

class BingoCliente:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BINGO")
        self.root.geometry("700x800")
        self.root.configure(bg="#0a0a0a")

        self.socket = None
        self.carton = {}
        self.marcados = set()
        self.botones = {}
        self.animacion_ids = []

        if not self.conectar_servidor():
            return

        self.crear_interfaz()
        threading.Thread(target=self.recibir_mensajes, daemon=True).start()
        self.root.mainloop()

    def conectar_servidor(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((HOST, PORT))
            data = self.socket.recv(1024).decode('utf-8')
            self.carton = json.loads(data)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar:\n{e}")
            return False

    def crear_interfaz(self):
        tk.Label(self.root, text="B I N G O", font=("Arial Black", 22), fg="#FFD700", bg="#0a0a0a").pack(pady=15)

        frame = tk.Frame(self.root, bg="#1a1a2e", relief="raised", bd=5)
        frame.pack(pady=10, padx=20)

        for col, letra in enumerate('BINGO'):
            tk.Label(frame, text=letra, font=("Arial Black", 14), width=6, height=2,
                     bg="#16213e", fg="white").grid(row=0, column=col, padx=1, pady=1)
            for row in range(5):
                num = self.carton[letra][row]
                btn = tk.Button(frame, text=str(num), font=("Arial", 16, "bold"),
                                width=6, height=2, bg="#f4f4f4", fg="#0f0f0f",
                                relief="flat", state="disabled")
                btn.grid(row=row+1, column=col, padx=1, pady=1)
                self.botones[num] = btn

        self.canvas = tk.Canvas(self.root, width=220, height=220, bg="#0a0a0a", highlightthickness=0)
        self.canvas.pack(pady=25)

        self.lbl_ultimo = tk.Label(self.root, text="Esperando...", font=("Arial", 14), fg="#ccc", bg="#0a0a0a")
        self.lbl_ultimo.pack(pady=5)

        self.btn_bingo = tk.Button(self.root, text="¡B I N G O !", font=("Arial Black", 18),
                                   bg="#FFD700", fg="black", width=18, height=2,
                                   command=self.enviar_bingo, state="disabled")
        self.btn_bingo.pack(pady=20)

    def cancelar_animacion(self):
        for id in self.animacion_ids:
            try: self.root.after_cancel(id)
            except: pass
        self.animacion_ids.clear()

    def dibujar_balota(self, letra, numero, angulo):
        self.canvas.delete("all")
        x, y = 110, 110
        r = 90
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#e74c3c", outline="#c0392b", width=6)
        self.canvas.create_text(x, y-25, text=letra, font=("Arial Black", 36), fill="white", angle=angulo)
        self.canvas.create_text(x, y+25, text=numero, font=("Arial Black", 36), fill="white", angle=angulo)

    def animar_balota(self, letra, numero_str):
        self.cancelar_animacion()
        self.btn_bingo.config(state="normal")
        self.lbl_ultimo.config(text=f"{letra}{numero_str}", fg="#e74c3c")

        for i in range(0, 360, 30):
            id = self.root.after(i * 20, self.dibujar_balota, letra, numero_str, i)
            self.animacion_ids.append(id)

        self.root.after(720, lambda: self.marcar_numero(letra, int(numero_str)))

    def marcar_numero(self, letra, numero):
        if numero in self.botones:
            self.botones[numero].config(bg="#f39c12", fg="white", relief="sunken")
            self.marcados.add(numero)
        for n in self.carton.get(letra, []):
            if n in self.botones:
                self.botones[n].config(state="normal")
        self.chequear_bingo()

    def chequear_bingo(self):
        tiene_bingo = any(
            all(n in self.marcados for n in self.carton.get(letra,numero, []))
            for letra in 'BINGO'
        )
        if tiene_bingo:
            self.btn_bingo.config(
                bg="#27ae60", fg="white", text="¡GRITAR BINGO!", state="normal"
            )
        else:
            self.btn_bingo.config(
                bg="#FFD700", fg="black", text="¡B I N G O !", state="disabled"
            )

    def enviar_bingo(self):
        try:
            self.socket.send("BINGO".encode())
            self.btn_bingo.config(state="disabled", text="ENVIADO...")
        except:
            pass

    def recibir_mensajes(self):
        while True:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data: break
                msg = json.loads(data)
                
                if msg["tipo"] == "numero":
                    self.animar_balota(msg["numero"][0], msg["numero"][1:])
                elif msg["tipo"] in ["ganaste", "perdiste"]:
                    messagebox.showinfo(
                        "BINGO" if msg["tipo"] == "ganaste" else "Juego Terminado",
                        msg["mensaje"]
                    )
                    self.root.quit()
                    break
            except:
                break

if __name__ == "__main__":
    BingoCliente()