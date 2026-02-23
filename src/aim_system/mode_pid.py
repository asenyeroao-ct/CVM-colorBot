def apply(dx, dy, distance_to_center, tracker, is_sec=False):
    from . import normal as legacy_normal

    legacy_normal._apply_pid_aim(dx, dy, distance_to_center, tracker, is_sec)


def reset(tracker, is_sec=False):
    from . import normal as legacy_normal

    legacy_normal._reset_pid_state(tracker, is_sec)
