import time
import os
import sys
from datetime import datetime
from pynput import mouse, keyboard

# --------- PARÁMETROS AJUSTABLES ---------
# 1) JITTER: vibración chica y rápida alrededor de la posición estable
JITTER_DIST_MAX = 15        # px: hasta esta distancia puede ser "temblor chico"
JITTER_INTERVAL_MAX = 0.25  # seg: si pasa en menos de 250 ms se considera temblor

# 2) JERK: sacudón brusco (movimiento grande y rápido)
JERK_DIST_MIN = 30          # px: por encima de esto puede ser "sacudón"
JERK_INTERVAL_MAX = 0.12    # seg: si pasa en menos de 120 ms

# -----------------------------------------

last_stable_pos = None
last_move_time = None
suppressing = False

mouse_controller = mouse.Controller()
running = True

last_positions = []  # por ahora solo para debug futuro si queremos
log_file = None


# ---------- LOG ----------
def get_log_path():
    # Carpeta donde está el .py o el .exe
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, "tremor_filter.log")


def init_log():
    global log_file
    try:
        path = get_log_path()
        log_file = open(path, "a", buffering=1, encoding="utf-8")  # line-buffered
        log(f"=== Inicio tremor_filter ({datetime.now().isoformat(timespec='seconds')}) ===")
        log(
            f"PARAMS: JITTER_DIST_MAX={JITTER_DIST_MAX}, "
            f"JITTER_INTERVAL_MAX={JITTER_INTERVAL_MAX}, "
            f"JERK_DIST_MIN={JERK_DIST_MIN}, "
            f"JERK_INTERVAL_MAX={JERK_INTERVAL_MAX}"
        )
    except Exception as e:
        print("No se pudo abrir el log:", e)


def close_log():
    global log_file
    if log_file:
        log(f"=== Fin tremor_filter ({datetime.now().isoformat(timespec='seconds')}) ===")
        try:
            log_file.close()
        except Exception:
            pass
        log_file = None


def log(msg: str):
    global log_file
    try:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n"
        if log_file:
            log_file.write(line)
        else:
            print(line, end="")
    except Exception:
        pass
# ------------------------


def distance(p1, p2):
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return (dx * dx + dy * dy) ** 0.5


def on_move(x, y):
    """
    Solo filtramos movimiento. No tocamos los clics.
    """
    global last_stable_pos, last_move_time, suppressing, last_positions

    if suppressing:
        return

    now = time.time()

    # Guardamos historial por si en el futuro queremos debug extra
    last_positions.append((now, (x, y)))
    last_positions[:] = [(t, pos) for t, pos in last_positions if now - t <= 1.0]

    # Primera vez: tomamos como posición estable
    if last_stable_pos is None:
        last_stable_pos = (x, y)
        last_move_time = now
        log(f"Posición estable inicial: {last_stable_pos}")
        return

    dist = distance((x, y), last_stable_pos)
    dt = now - last_move_time
    # Evitamos divisiones locas si dt es 0
    speed = dist / dt if dt > 0 else float("inf")

    # ---- REGLAS DE FILTRADO ----
    # 1) JITTER: movimiento chico y rápido cerca de la posición estable
    if dist <= JITTER_DIST_MAX and dt <= JITTER_INTERVAL_MAX:
        log(
            f"TEMBLOR_JITTER: actual={x,y}, estable={last_stable_pos}, "
            f"dist={dist:.2f}, dt={dt:.3f}, speed={speed:.2f}"
        )
        suppressing = True
        mouse_controller.position = last_stable_pos
        suppressing = False
        # No actualizamos last_stable_pos ni last_move_time
        return

    # 2) JERK: sacudón grande y rápido
    if dist >= JERK_DIST_MIN and dt <= JERK_INTERVAL_MAX:
        log(
            f"TEMBLOR_JERK: actual={x,y}, estable={last_stable_pos}, "
            f"dist={dist:.2f}, dt={dt:.3f}, speed={speed:.2f}"
        )
        suppressing = True
        mouse_controller.position = last_stable_pos
        suppressing = False
        # No actualizamos last_stable_pos ni last_move_time
        return

    # Si no es ni jitter ni jerk, lo consideramos movimiento intencional
    last_stable_pos = (x, y)
    last_move_time = now
    # Podrías loguear algunos movimientos "intencionales" cada tanto si querés:
    # log(f"MOV_OK: nueva estable={last_stable_pos}, dist={dist:.2f}, dt={dt:.3f}")


def on_click(x, y, button, pressed):
    """
    No filtramos clics. Solo opcionalmente logueamos si querés verlos.
    """
    if pressed:
        # Si querés menos ruido, comentá esta línea:
        log(f"Click (NO filtrado) en {x,y} ({button})")


def on_scroll(x, y, dx, dy):
    # Por ahora no tocamos el scroll
    pass


def on_key_press(key):
    global running
    try:
        if key == keyboard.Key.esc:
            log("ESC detectado, saliendo por pedido del usuario.")
            running = False
            return False
    except Exception as e:
        log(f"Error en on_key_press: {e}")


def main():
    init_log()
    print("Filtro de temblor (solo movimiento) iniciado. Ver tremor_filter.log para detalles.")
    print("Presioná ESC para cerrarlo.")

    log("Listeners de mouse y teclado iniciados.")

    with mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll
    ) as mouse_listener, keyboard.Listener(
        on_press=on_key_press
    ) as keyboard_listener:

        while running:
            time.sleep(0.01)

        mouse_listener.stop()
        keyboard_listener.stop()

    log("Listeners detenidos, cerrando programa.")
    close_log()


if __name__ == "__main__":
    main()
