from src.utils.debug_logger import log_print
import cv2
import numpy as np
from src.utils.config import config

# ------------------ Config GPU ------------------

# ------------------ Modèle HSV ------------------
_model = None
_class_names = {}
HSV_MIN = None
HSV_MAX = None
def test():
    log_print("HSV Detection test initialized")
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    hsv_img = cv2.cvtColor(dummy_img, cv2.COLOR_BGR2HSV)
    log_print("HSV conversion done")

def load_model(model_path=None):
    global _model, _class_names, HSV_MIN, HSV_MAX
    config.model_load_error = ""

    try:
        log_print("Loading HSV parameters...")
        yellow = [30, 125, 150, 30, 255, 255]
        purple = [144, 106, 172, 160, 255, 255]

        if config.color == "yellow":
            HSV_MIN = np.array([yellow[0], yellow[1], yellow[2]], dtype=np.uint8)
            HSV_MAX = np.array([yellow[3], yellow[4], yellow[5]], dtype=np.uint8)
            log_print("Loaded HSV for yellow")

        elif config.color == "purple":
            HSV_MIN = np.array([purple[0], purple[1], purple[2]], dtype=np.uint8)
            HSV_MAX = np.array([purple[3], purple[4], purple[5]], dtype=np.uint8)
            log_print("Loaded HSV for purple")

        elif config.color == "custom":
            # 使用自訂HSV值
            HSV_MIN = np.array([
                getattr(config, "custom_hsv_min_h", 0),
                getattr(config, "custom_hsv_min_s", 0),
                getattr(config, "custom_hsv_min_v", 0)
            ], dtype=np.uint8)
            HSV_MAX = np.array([
                getattr(config, "custom_hsv_max_h", 179),
                getattr(config, "custom_hsv_max_s", 255),
                getattr(config, "custom_hsv_max_v", 255)
            ], dtype=np.uint8)
            log_print(f"Loaded custom HSV: MIN={HSV_MIN}, MAX={HSV_MAX}")

        else:
            raise ValueError(f"Unknown color {config.color}")

        _model = (HSV_MIN, HSV_MAX)
        _class_names = {"color": "Target Color"}
        config.model_classes = list(_class_names.values())
        config.model_file_size = 0
        return _model, _class_names

    except Exception as e:
        config.model_load_error = f"Failed to load HSV params: {e}"
        _model, _class_names = None, {}
        return None, {}


def reload_model(model_path=None):
    return load_model(model_path)

# ------------------ Vérification ligne verticale ------------------
def has_color_vertical_line(mask, x, y1, y2):
    """
    Vérifie si une colonne verticale à la position x contient des pixels non nuls.
    """
    line = mask[y1:y2, x]
    return np.any(line > 0)

# ------------------ Fusion de rectangles ------------------
def merge_close_rects(rects, centers, dist_threshold=None):
    """
    合併相近的矩形
    
    Args:
        rects: 矩形列表
        centers: 中心點列表
        dist_threshold: 距離閾值（如果為 None，則從 config 讀取）
    """
    if dist_threshold is None:
        dist_threshold = getattr(config, "detection_merge_distance", 250)
    merged, merged_centers = [], []
    used = [False] * len(rects)

    for i, (r1, c1) in enumerate(zip(rects, centers)):
        if used[i]:
            continue
        x1, y1, w1, h1 = r1
        cx1, cy1 = c1
        nx, ny, nw, nh = x1, y1, w1, h1
        cxs, cys = [cx1], [cy1]

        for j, (r2, c2) in enumerate(zip(rects, centers)):
            if i == j or used[j]:
                continue
            x2, y2, w2, h2 = r2
            cx2, cy2 = c2

            # --- Condition 1 : chevauchement (重疊) ---
            overlap = (x1 < x2 + w2 and x1 + w1 > x2) and (y1 < y2 + h2 and y1 + h1 > y2)
            
            # --- Condition 2 : distance-based merging (距離合併) ---
            # 計算兩個矩形中心點之間的距離
            center_distance = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
            within_distance = center_distance <= dist_threshold
            
            # 如果重疊或距離足夠近，則合併
            if overlap or within_distance:
                nx, ny = min(nx, x2), min(ny, y2)
                nw = max(nx + nw, x2 + w2) - nx
                nh = max(ny + nh, y2 + h2) - ny
                cxs.append(cx2)
                cys.append(cy2)
                used[j] = True

        used[i] = True
        merged.append((nx, ny, nw, nh))
        merged_centers.append((int(np.mean(cxs)), int(np.mean(cys))))

    return merged, merged_centers

def triggerbot_detect(model, roi):
    """
    Détecte si la couleur est présente dans le ROI.
    Renvoie True si au moins un pixel détecté, False sinon.

    Params:
        model : tuple (HSV_MIN, HSV_MAX)
        roi : image BGR de la zone à analyser
    """
    if model is None or roi is None:
        return False

    # Conversion HSV et masque
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_roi, model[0], model[1])

    # Nettoyage morphologique léger
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Retourne True si au moins un pixel détecté
    return np.any(mask > 0)


# ------------------ Détection couleur ------------------
def perform_detection(model, image):
    """
    Détecte les zones colorées dans l'image et fusionne les rectangles proches.
    """
    if model is None:
        return None

    hsv_img = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_img, model[0], model[1])

    # Nettoyage morphologique
    kernel = np.ones((30, 15), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)

   

    # Contours et rectangles
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects, centers = [], []
    
    # 獲取最小輪廓點數配置
    min_contour_points = getattr(config, "detection_min_contour_points", 5)
    
    for c in contours:
        # 過濾：跳過點數太少的輪廓
        if len(c) < min_contour_points:
            continue
            
        x, y, w, h = cv2.boundingRect(c)
        cx, cy = x + w // 2, y + h // 2

        # --- Condition 2 : skip si pas de ligne verticale colorée ---
        if not has_color_vertical_line(mask, cx, y, y + h):
            continue

        rects.append((x, y, w, h))
        centers.append((cx, cy))

    # 使用 config 中的 merge_distance（不傳遞參數，讓函數從 config 讀取）
    merged_rects, merged_centers = merge_close_rects(rects, centers)

    return [{"class": "player", "bbox": r, "confidence": 1.0} for r in merged_rects], mask

# ------------------ Helpers ------------------
def get_class_names():
    return _class_names

def get_model_size(model_path=None):
    return 0

