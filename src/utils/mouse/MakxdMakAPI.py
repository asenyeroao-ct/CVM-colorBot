from . import MakV2Binary


def connect(port: str = None, baud: int = None):
    return MakV2Binary.connect(port=port, baud=baud, backend_name="MakxdMakAPI", log_name="MakxdMakAPI")


def disconnect():
    MakV2Binary.disconnect()


def is_button_pressed(idx: int) -> bool:
    return MakV2Binary.is_button_pressed(idx)


def move(x: float, y: float):
    MakV2Binary.move(x, y)


def move_bezier(x: float, y: float, segments: int, ctrl_x: float, ctrl_y: float):
    MakV2Binary.move_bezier(x, y, segments, ctrl_x, ctrl_y)


def left(isdown: int):
    MakV2Binary.left(isdown)


def right(isdown: int):
    MakV2Binary.right(isdown)


def middle(isdown: int):
    MakV2Binary.middle(isdown)


def key_down(key):
    MakV2Binary.key_down(key)


def key_up(key):
    MakV2Binary.key_up(key)


def key_press(key):
    MakV2Binary.key_press(key)


def is_key_pressed(key) -> bool:
    return MakV2Binary.is_key_pressed(key)


def lock_button_idx(idx: int):
    MakV2Binary.lock_button_idx(idx)


def unlock_button_idx(idx: int):
    MakV2Binary.unlock_button_idx(idx)


def unlock_all_locks():
    MakV2Binary.unlock_all_locks()


def lock_movement_x(lock: bool = True, skip_lock: bool = False):
    MakV2Binary.lock_movement_x(lock=lock, skip_lock=skip_lock)


def lock_movement_y(lock: bool = True, skip_lock: bool = False):
    MakV2Binary.lock_movement_y(lock=lock, skip_lock=skip_lock)


def update_movement_lock(lock_x: bool, lock_y: bool, is_main: bool = True):
    MakV2Binary.update_movement_lock(lock_x=lock_x, lock_y=lock_y, is_main=is_main)


def tick_movement_lock_manager():
    MakV2Binary.tick_movement_lock_manager()


def mask_manager_tick(selected_idx: int, aimbot_running: bool):
    MakV2Binary.mask_manager_tick(selected_idx=selected_idx, aimbot_running=aimbot_running)
