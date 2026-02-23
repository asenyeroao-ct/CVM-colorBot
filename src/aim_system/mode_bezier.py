def apply(dx, dy, distance_to_center, tracker, is_sec=False):
    from . import normal as legacy_normal

    legacy_normal._apply_bezier_aim(dx, dy, distance_to_center, tracker, is_sec)
