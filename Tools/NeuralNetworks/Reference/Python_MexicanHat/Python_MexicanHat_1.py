import cv2
import numpy as np

# === CONSTANTS ===
BLU, GRN, RED = 0, 1, 2
HUE, SAT, INT = 0, 1, 2

# === INITIAL IMAGE SETUP ===
img = np.zeros((200, 200, 3), dtype=np.uint8)
img[:, :100, BLU] = 128  # left half blue
img[:, 100:, RED] = 255  # right half red
cv2.line(img, (10, 10), (190, 190), (0, 255, 0), 5, cv2.LINE_AA)
cv2.putText(img, "test text", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)

# === BLACK & WHITE IMAGE PREP ===
blank = np.zeros((400, 300), dtype=np.uint8)
unity = np.ones((400, 300), dtype=np.uint8)
img_red = np.zeros((400, 300, 3), dtype=np.uint8)
img_gray = np.full((400, 300, 3), 128, dtype=np.uint8)
hue_mask = np.zeros((400, 300, 3), dtype=np.uint8)
unity_red = np.zeros((400, 300, 3), dtype=np.uint8)

# Red channel fill and HSV masks
img_red[:, :, RED] = 128
hue_mask[:, :, SAT] = 255
hue_mask[:, :, INT] = 255
unity_red[:, :, RED] = 1

# Add a single white pixel for Gaussian
blank[150, 50] = 255

# === SMOOTH AND NORMALIZE BLANK ===
for _ in range(3):
    blank = cv2.GaussianBlur(blank, (45, 45), 0)
    norm = np.linalg.norm(blank)
    f_const = 128.0 / norm if norm > 0 else 1
    blank = cv2.multiply(blank.astype(np.float32), unity.astype(np.float32), scale=f_const).astype(np.uint8)

# === CONVERT img_red FROM HSV TO BGR ===
img_red = cv2.cvtColor(img_red, cv2.COLOR_HSV2BGR)

# === GPS PROBABILITY MAP ===
prob_gps = np.zeros((400, 300), dtype=np.uint8)
for x, y, val in [(150, 200, 255), (130, 190, 192), (140, 180, 164)]:
    prob_gps[y, x] = val

for _ in range(6):
    prob_gps = cv2.GaussianBlur(prob_gps, (45, 45), 0)
    norm = np.linalg.norm(prob_gps)
    f_const = 128.0 / norm if norm > 0 else 1
    prob_gps = cv2.multiply(prob_gps.astype(np.float32), unity.astype(np.float32), scale=f_const).astype(np.uint8)

# === MODIFY img_red BASED ON prob_gps ===
img_red = cv2.cvtColor(prob_gps, cv2.COLOR_GRAY2BGR)
img_red = cv2.bitwise_not(img_red)
img_red = cv2.subtract(img_red, img_gray)
img_red[:, :, SAT] = 255
img_red[:, :, INT] = 255
img_red = cv2.cvtColor(img_red, cv2.COLOR_HSV2BGR)

# === ENCODER PROBABILITY MAP ===
prob_enc = np.zeros((400, 300), dtype=np.uint8)
for x, y, val in [(175, 225, 255), (200, 225, 192), (175, 250, 164)]:
    prob_enc[y, x] = val

for _ in range(6):
    prob_enc = cv2.GaussianBlur(prob_enc, (45, 45), 0)
    norm = np.linalg.norm(prob_enc)
    f_const = 128.0 / norm if norm > 0 else 1
    prob_enc = cv2.multiply(prob_enc.astype(np.float32), unity.astype(np.float32), scale=f_const).astype(np.uint8)

# === COMBINED GPS + ENCODER MAP ===
f_const = 255.0 / (128 * 128)
prob_comb = cv2.multiply(prob_gps.astype(np.float32), prob_enc.astype(np.float32), scale=f_const).astype(np.uint8)

# === MEXICAN HAT NEGATIVE MASK ===
mex_neg = np.full((400, 300), 128, dtype=np.uint8)
cv2.circle(mex_neg, (150, 200), 40, 0, -1)

# === MEXICAN HAT POSITIVE GAUSSIAN ===
mex_pos = np.zeros((400, 300), dtype=np.uint8)
mex_pos[200, 150] = 255
for _ in range(6):
    mex_pos = cv2.GaussianBlur(mex_pos, (45, 45), 0)
    norm = np.linalg.norm(mex_pos)
    f_const = 128.0 / norm if norm > 0 else 1
    mex_pos = cv2.multiply(mex_pos.astype(np.float32), unity.astype(np.float32), scale=f_const).astype(np.uint8)

# === COMBINED MEXICAN HAT ===
mex_comb = cv2.add(mex_pos, mex_neg)

# === SAVE RESULTS TO FILE ===
cv2.imwrite("img_line_text.png", img)
cv2.imwrite("imageBlank.png", blank)
cv2.imwrite("imageRed.png", img_red)
cv2.imwrite("imageProbGPS.png", prob_gps)
cv2.imwrite("imageProbENC.png", prob_enc)
cv2.imwrite("imageProbComb.png", prob_comb)
cv2.imwrite("mexNeg.png", mex_neg)
cv2.imwrite("mexPos.png", mex_pos)
cv2.imwrite("mexComb.png", mex_comb)
