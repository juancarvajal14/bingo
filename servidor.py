# servidor.py
import socket
import threading
import random
import json
import time

HOST = '127.0.0.1'
PORT = 65432

RANGOS = {
    'B': (1, 15), 'I': (16, 30), 'N': (31, 45),
    'G': (46, 60), 'O': (61, 75)
}

# --- Estado del juego -------------------------------------------------
numeros_usados = set()
clientes = []                     # sockets activos
nombres_clientes = {}             # addr → nombre
cartones_por_cliente = {}         # addr → cartón
marcados_por_cliente = {}         # addr → set de números marcados
lock = threading.Lock()
ganador_encontrado = False
evento_parar = threading.Event()  # detiene todos los hilos
# ---------------------------------------------------------------------

def generar_carton():
    carton = {}
    for letra, (min_val, max_val) in RANGOS.items():
        carton[letra] = random.sample(range(min_val, max_val + 1), 5)
    return carton

def generar_numero():
    while True:
        letra = random.choice(list(RANGOS.keys()))
        min_val, max_val = RANGOS[letra]
        num = random.randint(min_val, max_val)
        if num not in numeros_usados:
            with lock:
                numeros_usados.add(num)
            return f"{letra}{num}"

def verificar_bingo_real(marcados, carton):
    """Devuelve True si el cliente tiene al menos una columna completa."""
    return any(all(n in marcados for n in carton[letra]) for letra in 'BINGO')

# --------------------------------------------------------------------- manejador de cliente
def manejar_cliente(conn, addr):
    global ganador_encontrado, clientes, nombres_clientes, cartones_por_cliente, marcados_por_cliente  # ← AQUÍ ESTÁ LA SOLUCIÓN

    # --- Registro del jugador -------------------------------------------------
    nombre = f"Jugador_{len(clientes)+1}"
    with lock:
        nombres_clientes[addr] = nombre
        clientes.append(conn)

    print(f"{nombre} conectado ({len(clientes)}/{num_jugadores})")

    # --- Envío del cartón ------------------------------------------------------
    carton = generar_carton()
    with lock:
        cartones_por_cliente[addr] = carton
        marcados_por_cliente[addr] = set()
    conn.send(json.dumps(carton).encode())

    # --- Bucle de recepción ----------------------------------------------------
    try:
        while not evento_parar.is_set():
            try:
                conn.settimeout(1.0)
                data = conn.recv(1024).decode()
                if not data:
                    break

                # Mensajes JSON (marcar número) o texto plano (BINGO)
                try:
                    msg = json.loads(data)
                    if msg["tipo"] == "marcar":
                        numero = msg["numero"]
                        with lock:
                            marcados_por_cliente[addr].add(numero)
                        continue
                except Exception:
                    pass

                # --- BINGO ----------------------------------------------------
                if data == "BINGO":
                    with lock:
                        if not ganador_encontrado:
                            marcados = marcados_por_cliente.get(addr, set())
                            carton = cartones_por_cliente.get(addr, {})
                            if verificar_bingo_real(marcados, carton):
                                ganador_encontrado = True
                                ganador = nombres_clientes[addr]
                                print(f"¡{ganador} GANÓ CON BINGO VÁLIDO!")
                                anunciar_ganador(conn, ganador)
                                evento_parar.set()
                            else:
                                print(f"{nombres_clientes[addr]} intentó BINGO inválido.")
                                conn.send(json.dumps({
                                    "tipo": "error",
                                    "mensaje": "¡BINGO INVÁLIDO! No tienes una columna completa."
                                }).encode())
            except socket.timeout:
                continue
            except Exception:
                break
    finally:
        with lock:
            clientes = [c for c in clientes if c != conn]
        conn.close()

# --------------------------------------------------------------------- anuncio de ganador
def anunciar_ganador(ganador_conn, nombre_ganador):
    msg_ganador = json.dumps({
        "tipo": "ganaste",
        "mensaje": f"¡{nombre_ganador} - BINGO! ¡ERES EL GANADOR!"
    })
    msg_perdedor = json.dumps({
        "tipo": "perdiste",
        "mensaje": f"{nombre_ganador} gritó BINGO. ¡Juego terminado!"
    })

    for cliente in clientes[:]:
        try:
            if cliente == ganador_conn:
                cliente.send(msg_ganador.encode())
            else:
                cliente.send(msg_perdedor.encode())
        except Exception:
            pass
        finally:
            try:
                cliente.close()
            except Exception:
                pass
    with lock:
        clientes.clear()

# --------------------------------------------------------------------- espera de jugadores
def esperar_jugadores(num_jugadores):
    print(f"\nEsperando {num_jugadores} jugadores en {HOST}:{PORT}...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    while len(clientes) < num_jugadores and not evento_parar.is_set():
        try:
            server.settimeout(1.0)
            conn, addr = server.accept()
            threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()
        except socket.timeout:
            continue
        except Exception:
            break
    server.close()

# --------------------------------------------------------------------- main
def main():
    global num_jugadores

    # ---- Preguntar número de jugadores ------------------------------------
    while True:
        try:
            num_jugadores = int(input("\n¿Cuántos jugadores? (2-10): "))
            if 2 <= num_jugadores <= 10:
                break
        except Exception:
            pass

    # ---- Esperar conexiones -----------------------------------------------
    esperar_jugadores(num_jugadores)

    if len(clientes) < 2:
        print("No hay suficientes jugadores.")
        return

    print(f"\n¡{len(clientes)} jugadores listos! JUEGO INICIADO")
    input("\nPresiona ENTER para la primera bolita...\n")

    # ---- Bucle principal del juego -----------------------------------------
    while not evento_parar.is_set():
        numero = generar_numero()
        print(f"→ {numero}")

        msg = json.dumps({"tipo": "numero", "numero": numero}).encode()
        with lock:
            for cliente in clientes[:]:
                try:
                    cliente.send(msg)
                except Exception:
                    clientes.remove(cliente)

        if evento_parar.is_set():
            break

        try:
            entrada = input("Enter para siguiente (o 'q' para salir): ")
            if entrada.lower() == 'q':
                evento_parar.set()
                break
        except Exception:
            break

    print("\nJUEGO TERMINADO")
    time.sleep(2)

if __name__ == "__main__":
    main()