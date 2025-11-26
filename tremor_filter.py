import time
import os
import sys
from datetime import datetime
from pynput import mouse, keyboard

# --------- PARÁMETROS AJUSTABLES ---------
# Radio alrededor de la posición filtrada en el que ignoramos movimiento (temblor chico)
DEADZONE_RADIUS = 20      # px

# Cuánto del movimiento hacia el objetivo aplicamos en cada paso (0 < SMOOTHING <= 1)
SMOOTHING_FACTOR = 0.25   # 0.25 = el cursor recorre aprox el 25% del camino cada vez

# Paso máximo por actualización (para recortar sacudones muy grandes)
MAX_STEP = 35             # px
# -----------------------------------------

filtered_pos = None       # posición "real" que usamos para el cursor
suppressing = False
running = True

log_file = None


# ---------- LOG ----------
def get_log_path():
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, "tremor_filter.log")


def init_log():
    global log_file
    try:
        path = get_log_path()
        log_file = open(path, "a", buffering=1, encoding="utf-8")
        log(f"=== Inicio tremor_filter suavizado ({datetime.now().isoformat(timespec='seconds')}) ===")
        log(
            f"PARAMS: DEADZONE_RADIUS={DEADZONE_RADIUS}, "
            f"SMOOTHING_FACTOR={SMOOTHING_FACTOR}, "
            f"MAX_STEP={MAX_STEP}"
        )
    except Exception as e:
        print("No se pudo abrir el log:", e)


def close_log():
    global log_file
    if log_file:
        log(f"=== Fin tremor_filter suavizado ({datetime.now().isoformat(timespec='seconds')}) ===")
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


mouse_controller = mouse.Controller()


def on_move(x, y):
    """
    Tomamos el movimiento bruto (x, y) pero SIEMPRE dibujamos una versión suavizada
    alrededor de filtered_pos.
    """
    global filtered_pos, suppressing

    if suppressing:
        return

    raw_pos = (x, y)

    # Primera vez: tomamos como punto de partida
    if filtered_pos is None:
        filtered_pos = raw_pos
        log(f"Posición inicial filtrada: {filtered_pos}")
        return

    dist = distance(raw_pos, filtered_pos)

    # 1) Si está dentro de la deadzone, lo ignoramos (temblor chico)
    if dist <= DEADZONE_RADIUS:
        # Opcional: loguear sólo si querés ver cuánto jitter está ignorando
        # log(f"IGNORED_JITTER: raw={raw_pos}, filtered={filtered_pos}, dist={dist:.2f}")
        suppressing = True
        mouse_controller.position = filtered_pos
        suppressing = False
        return

    # 2) Si está fuera de la deadzone, nos movemos hacia ahí, pero suavizado
    # Calculamos cuánto nos queremos mover en esta actualización
    step = dist * SMOOTHING_FACTOR  # sólo una fracción del camino
    if step > MAX_STEP:
        step = MAX_STEP  # recortamos sacudones enormes

    ratio = step / dist  # factor para escalar el vector dirección

    dx = (raw_pos[0] - filtered_pos[0]) * ratio
    dy = (raw_pos[1] - filtered_pos[1]) * ratio

    new_pos = (filtered_pos[0] + dx, filtered_pos[1] + dy)

    log(
        f"MOVE_FILTERED: raw={raw_pos}, from={filtered_pos}, to={new_pos}, "
        f"dist_raw={dist:.2f}, step={step:.2f}"
    )

    filtered_pos = new_pos

    suppressing = True
    mouse_controller.position = new_pos
    suppressing = False


def on_click(x, y, button, pressed):
    # No tocamos clics, solo si querés verlos:
    if pressed:
        log(f"Click en {x,y} ({button})")


def on_scroll(x, y, dx, dy):
    # No modificamos scroll
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
    print("Filtro de temblor (suavizado con deadzone) iniciado. Ver tremor_filter.log para detalles.")
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
