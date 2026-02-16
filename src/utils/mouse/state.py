import threading

makcu = None
makcu_lock = threading.Lock()

button_states = {i: False for i in range(5)}
button_states_lock = threading.Lock()

is_connected = False
active_backend = "Serial"
last_connect_error = ""

kmnet_module = None
kmboxa_module = None
makv2_module = None
dhz_client = None

last_button_mask = 0
listener_thread = None

mask_applied_idx = None

movement_lock_state = {
    "lock_x": False,
    "lock_y": False,
    "main_aimbot_locked": False,
    "sec_aimbot_locked": False,
    "last_main_move_time": 0.0,
    "last_sec_move_time": 0.0,
    "lock": threading.Lock(),
}


def set_connected(connected: bool, backend: str = None):
    global is_connected, active_backend
    is_connected = bool(connected)
    if backend is not None:
        active_backend = backend


def reset_button_states():
    global last_button_mask
    with button_states_lock:
        for i in range(5):
            button_states[i] = False
    last_button_mask = 0
