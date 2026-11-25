"""One-off helper: turns the raw Google Maps screenshot (img_1.png) into a clean,
UI-free campus map (campus_map.png).  Run once:  python prep_map.py"""

from pathlib import Path

import cv2
import numpy as np

SRC = Path(__file__).with_name("img_1.png")
DST = Path(__file__).with_name("campus_map.png")

img = cv2.imread(str(SRC))  # pylint: disable=no-member
orig = img.copy()

# 1) Cover the Google Maps buttons with nearby real map texture,
#    feathered at the edges.  (target centre, patch size, source centre)
PATCHES = [
    ((527, 233), (70, 70), (470, 420)),  # layers button
    ((527, 310), (70, 70), (515, 385)),  # compass
    ((515, 877), (92, 92), (505, 690)),  # location button
    ((515, 964), (100, 100), (480, 640)),  # directions button
]
for (cx, cy), (w, h), (sx, sy) in PATCHES:
    src = orig[sy - h // 2 : sy + h // 2, sx - w // 2 : sx + w // 2].astype(np.float32)
    alpha = np.zeros((h, w), np.float32)
    alpha[10:-10, 10:-10] = 1.0
    alpha = cv2.GaussianBlur(alpha, (0, 0), 4)[..., None]
    y0, x0 = cy - h // 2, cx - w // 2
    y1, x1 = y0 + h, min(x0 + w, img.shape[1])
    ww = x1 - x0
    dst = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = (
        src[:, :ww] * alpha[:, :ww] + dst * (1 - alpha[:, :ww])
    ).astype(np.uint8)

# keep the "MIT dormitories" label that sits just under the layers button
img[260:274, 440:574] = orig[260:274, 440:574]

# 2) Remove the blue "you are here" dot and tone down its blue accuracy glow
dot = np.zeros(img.shape[:2], np.uint8)
cv2.circle(dot, (218, 832), 15, 255, -1)
img = cv2.inpaint(img, dot, 9, cv2.INPAINT_TELEA)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
glow = np.zeros(img.shape[:2], bool)
cv2.circle(glow.view(np.uint8), (218, 832), 46, 1, -1)
blue = glow & (hsv[..., 0] > 100) & (hsv[..., 0] < 135) & (hsv[..., 1] > 60)
hsv[..., 1][blue] *= 0.3
hsv[..., 2][blue] *= 0.8
img = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

# 3) Crop away the search bar (top) and the bottom sheet
img = img[184:1020, :]
cv2.imwrite(str(DST), img)
print("saved", DST.name, img.shape[1], "x", img.shape[0])
