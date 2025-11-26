import time
import os
import sys
from datetime import datetime
from pynput import mouse, keyboard

# --------- PARÁMETROS AJUSTABLES ---------
MAX_TREMOR_DISTANCE = 5       # px: qué tan chico es un movimiento tipo temblor
MAX_TREMOR_INTERVAL = 0.05    # seg: ventana de tiempo para temblor (50 ms)

MAX_CLICK_MOVE_DISTANCE = 20  # px: movimiento grande antes de clic = sospechoso
MAX_CLICK_LOOKBACK = 0.15     # seg: miramos 150 ms antes del clic
# -----------------------------------------

last_stable_pos = None
last_move_time = None
suppressing = False

mouse_controller = mouse.Controller()
running = True

last_positions = []  # lista de (timestamp, (x, y))

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
        log(f"PARAMS: MAX_TREMOR_DISTANCE={MAX_TREMOR_DISTANCE}, "
            f"MAX_TREMOR_INTERVAL={MAX_TREMOR_INTERVAL}, "
            f"MAX_CLICK_MOVE_DISTANCE={MAX_CLICK_MOVE_DISTANCE}, "
            f"MAX_CLICK_LOOKBACK={MAX_CLICK_LOOKBACK}")
    except Exception as e:
        # Si falla el log, seguimos igual
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
    """Escribe una línea en el log con timestamp."""
    global log_file
    try:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n"
        if log_file:
            log_file.write(line)
        else:
            # fallback por si algo raro pasó
            print(line, end="")
    except Exception:
        # nunca queremos romper por el log
        pass
# ------------------------


def distance(p1, p2):
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return (dx * dx + dy * dy) ** 0.5


def on_move(x, y):
    global last_stable_pos, last_move_time, suppressing, last_positions

    if suppressing:
        return

    now = time.time()

    # Guardamos historial reciente para el filtro de clics
    last_positions.append((now, (x, y)))
    last_positions = [(t, pos) for t, pos in last_positions if now - t <= 1.0]

    if last_stable_pos is None:
        last_stable_pos = (x, y)
        last_move_time = now
        log(f"Posición estable inicial: {last_stable_pos}")
        return

    dist = distance((x, y), last_stable_pos)
    dt = now - last_move_time

    if dist <= MAX_TREMOR_DISTANCE and dt <= MAX_TREMOR_INTERVAL:
        # Temblor detectado
        log(f"TEMBLOR movimiento: actual={x,y}, estable={last_stable_pos}, "
            f"dist={dist:.2f}, dt={dt:.3f}")
        suppressing = True
        mouse_controller.position = last_stable_pos
        suppressing = False
    else:
        # Movimiento intencional
        last_stable_pos = (x, y)
        last_move_time = now


def was_recent_large_movement():
    if not last_positions:
        return False

    now = time.time()
    recent = [(t, pos) for t, pos in last_positions if now - t <= MAX_CLICK_LOOKBACK]

    if len(recent) < 2:
        return False

    t0, p0 = recent[0]
    t1, p1 = recent[-1]

    dist = distance(p0, p1)
    return dist > MAX_CLICK_MOVE_DISTANCE


def on_click(x, y, button, pressed):
    global suppressing

    if not pressed:
        return

    if was_recent_large_movement():
        log(f"CLICK SUPRIMIDO en {x,y} (movimiento grande justo antes)")
        suppressing = True
        try:
            mouse_controller.release(button)
        except Exception as e:
            log(f"Error al soltar botón: {e}")
        suppressing = False
    else:
        log(f"Click permitido en {x,y} ({button})")


def on_scroll(x, y, dx, dy):
    # Si querés, podés loguear scroll también
    # log(f"Scroll en {x,y} dx={dx} dy={dy}")
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
    print("Filtro de temblor y clics iniciado. Ver tremor_filter.log para detalles.")
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
