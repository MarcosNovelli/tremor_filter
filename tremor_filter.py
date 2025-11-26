import time
from pynput import mouse, keyboard

# --------- PARÁMETROS AJUSTABLES ---------
# Distancia máxima (en píxeles) que consideramos "temblor" de movimiento
MAX_TREMOR_DISTANCE = 5

# Tiempo máximo (en segundos) entre pequeños movimientos para considerarlos temblor
MAX_TREMOR_INTERVAL = 0.05  # 50 ms

# Distancia máxima permitida justo antes de un clic para considerarlo "intencional"
MAX_CLICK_MOVE_DISTANCE = 20

# Tiempo máximo (en segundos) antes del clic que miramos para validar el movimiento
MAX_CLICK_LOOKBACK = 0.15  # 150 ms
# -----------------------------------------

last_stable_pos = None
last_move_time = None
suppressing = False  # para no entrar en bucle cuando movemos nosotros el cursor

mouse_controller = mouse.Controller()

running = True  # para cerrar el programa con ESC

# Para el filtro de clics:
last_positions = []  # lista de (timestamp, (x, y))


def distance(p1, p2):
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return (dx * dx + dy * dy) ** 0.5


def on_move(x, y):
    global last_stable_pos, last_move_time, suppressing, last_positions

    if suppressing:
        # Este movimiento lo generamos nosotros, lo ignoramos
        return

    now = time.time()

    # Guardamos historial reciente para el filtro de clics
    last_positions.append((now, (x, y)))
    # Limpiamos posiciones muy viejas
    last_positions = [(t, pos) for t, pos in last_positions if now - t <= 1.0]

    # Primera vez: tomamos como posición estable
    if last_stable_pos is None:
        last_stable_pos = (x, y)
        last_move_time = now
        return

    dist = distance((x, y), last_stable_pos)
    dt = now - last_move_time

    # Si se movió muy poquito y muy rápido => lo consideramos temblor
    if dist <= MAX_TREMOR_DISTANCE and dt <= MAX_TREMOR_INTERVAL:
        suppressing = True
        mouse_controller.position = last_stable_pos
        suppressing = False
        # No actualizamos last_stable_pos ni last_move_time (ruido)
    else:
        # Movimiento "real"
        last_stable_pos = (x, y)
        last_move_time = now


def was_recent_large_movement():
    """
    Devuelve True si justo antes del clic hubo un movimiento grande,
    lo que puede indicar un clic accidental por temblor.
    """
    if not last_positions:
        return False

    now = time.time()
    # Nos quedamos con posiciones en la ventana de tiempo de interés
    recent = [(t, pos) for t, pos in last_positions if now - t <= MAX_CLICK_LOOKBACK]

    if len(recent) < 2:
        return False

    # Comparamos la primera y la última en la ventana
    t0, p0 = recent[0]
    t1, p1 = recent[-1]

    dist = distance(p0, p1)
    return dist > MAX_CLICK_MOVE_DISTANCE


def on_click(x, y, button, pressed):
    global suppressing

    # Sólo filtramos cuando se PRESIONA el botón (no al soltar)
    if not pressed:
        return

    # Si detectamos que justo antes hubo un movimiento fuerte, lo tomamos como clic accidental
    if was_recent_large_movement():
        # Cancelamos el clic re-soltando el botón rápidamente (simulamos que no pasó)
        suppressing = True
        try:
            mouse_controller.release(button)
        except Exception:
            pass
        suppressing = False
    else:
        # Clic normal: no lo tocamos
        pass


def on_scroll(x, y, dx, dy):
    # No tocamos la rueda
    pass


def on_key_press(key):
    global running
    try:
        # Si aprieta ESC, cerramos el programa
        if key == keyboard.Key.esc:
            running = False
            return False  # corta el listener de teclado
    except Exception:
        pass


def main():
    print("Filtro de temblor y clics iniciado.")
    print("Presioná ESC para cerrarlo.")

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


if __name__ == "__main__":
    main()
