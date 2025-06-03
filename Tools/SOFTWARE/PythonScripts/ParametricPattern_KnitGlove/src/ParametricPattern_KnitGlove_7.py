import cv2
import numpy as np
import os
from datetime import datetime
import math

# ---- CONFIGURATION ----
palmWidthRatio = 1.696
palmHeightRatio = 2.261
wristHeightRatio = 1.391
castoffRow = 1
buffer = 1

# Simulate CLI arguments (you can later switch this to argparse)
class Args:
    lengthPalm = 10.0
    circumferencePalm = 8.0
    patternType = "B"  # Use "S" for snake

args = Args()

# ---- ROUNDING HELPERS ----
def round_even(x):
    return int(round(x)) if int(round(x)) % 2 == 0 else int(round(x) + 1) if x > int(x) else int(round(x) - 1)

def round_odd(x):
    return int(round(x)) if int(round(x)) % 2 != 0 else int(round(x) + 1) if x > int(x) else int(round(x) - 1)

# ---- CALCULATE MEASUREMENTS ----
raw_palmWidth = args.circumferencePalm * palmWidthRatio
raw_thumbWidth = raw_palmWidth / 4
raw_palmHeight = args.lengthPalm * palmHeightRatio
raw_wristHeight = args.lengthPalm * wristHeightRatio

palmWidth = round_odd(raw_palmWidth)
thumbWidth = round_even(raw_thumbWidth)
palmHeight = round_even(raw_palmHeight)
wristHeight = round_even(raw_wristHeight)
fingerRibHeight = round_odd(palmHeight / 3)
thumbDrop = round_even(0.4 * palmWidth)

width = palmWidth + thumbWidth + buffer * 2
height = palmHeight + wristHeight + castoffRow + buffer * 2
image = np.full((height, width, 3), fill_value=192, dtype=np.uint8)

# ---- COMMON START/END COORDINATES ----
start_x = buffer + (thumbWidth // 2)
end_x = start_x + palmWidth - 1
finger_start_y = buffer + castoffRow
finger_end_y = finger_start_y + fingerRibHeight - 1

# ---- WRIST RIB KNIT ----
wrist_start_y = height - buffer - castoffRow - wristHeight + 1
wrist_end_y = wrist_start_y + wristHeight - 1
cv2.rectangle(image, (start_x, wrist_start_y), (end_x, wrist_end_y), (0, 0, 255), -1)
colors = [(0, 0, 255), (0, 255, 0), (0, 255, 255), (255, 0, 0)]
for i in range(start_x, end_x + 1):
    image[wrist_end_y, i] = colors[(i - start_x) % len(colors)]
for x in range(start_x + 3, end_x - 1, 2):
    for y in range(wrist_end_y - 3, wrist_start_y, -1):
        image[y, x] = (0, 255, 0)

# ---- FINGER RIB KNIT ----
cv2.rectangle(image, (start_x, finger_start_y), (end_x, finger_end_y), (0, 0, 255), -1)
for x in range(start_x + 3, end_x - 1, 2):
    for y in range(finger_end_y - 1, finger_start_y + 1, -1):
        image[y, x] = (0, 255, 0)

# ---- PALM CABLE KNIT ----
palm_cable_start_y = finger_end_y + 1
palm_cable_height = palmHeight - fingerRibHeight
palm_cable_end_y = palm_cable_start_y + palm_cable_height - 1
cv2.rectangle(image, (start_x, palm_cable_start_y), (end_x, palm_cable_end_y), (0, 0, 255), -1)

center_y = palm_cable_start_y + palm_cable_height // 2
numberCableLinks = palm_cable_height // 4
isCableLinkOdd = (numberCableLinks % 2 != 0)

braided_w, braided_h = 6, 3
snake_w, snake_h = 4, 3
start_offset_x = 5

numberBraidedCables = math.floor(((palmWidth / 2) - 4) / 7)
numberSnakeCables = math.floor(((palmWidth / 2) - 4) / 5)
numCables = numberBraidedCables if args.patternType == "B" else numberSnakeCables

for i in range(numCables):
    cable_x = start_x + start_offset_x + i * (braided_w + 2)
    image[palm_cable_start_y:palm_cable_end_y + 1, cable_x] = (0, 255, 0)

    if not isCableLinkOdd:
        if args.patternType == "B":
            ly = center_y - braided_h - 1
            ry = center_y + 1
            cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (0, 0, 255), -1)
            cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (0, 0, 255), -1)
            image[ly + 1, cable_x + 3] = (255, 0, 255)
            image[ly + 1, cable_x + 4] = (255, 0, 255)
            image[ly + 1, cable_x + 1] = (255, 255, 0)
            image[ly + 1, cable_x + 2] = (255, 255, 0)
            image[ry + 1, cable_x + 3] = (255, 0, 255)
            image[ry + 1, cable_x + 4] = (255, 0, 255)
            image[ry + 1, cable_x + 5] = (255, 255, 0)
            image[ry + 1, cable_x + 6] = (255, 255, 0)
        elif args.patternType == "S":
            ly = center_y - snake_h - 1
            ry = center_y + 1
            cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (0, 0, 255), -1)
            cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (0, 0, 255), -1)
            image[ly + 1, cable_x + 1] = (255, 0, 255)
            image[ly + 1, cable_x + 2] = (255, 0, 255)
            image[ly + 1, cable_x + 3] = (255, 255, 0)
            image[ly + 1, cable_x + 4] = (255, 255, 0)
            image[ry + 1, cable_x + 1] = (255, 255, 0)
            image[ry + 1, cable_x + 2] = (255, 255, 0)
            image[ry + 1, cable_x + 3] = (255, 0, 255)
            image[ry + 1, cable_x + 4] = (255, 0, 255)

    cable_right_x = cable_x + (braided_w if args.patternType == "B" else snake_w) + 1
    image[palm_cable_start_y:palm_cable_end_y + 1, cable_right_x] = (0, 255, 0)

# ---- THUMB DROP LEFT ----
num_thumb_drops = thumbWidth // 2
for i in range(num_thumb_drops):
    dx = start_x - thumbWidth // 2 + i
    dy = finger_start_y + thumbDrop + i * 2
    cv2.rectangle(image, (dx, dy), (dx + thumbWidth // 2 - 1, dy + 1), (0, 0, 255), -1)
    image[dy + 1, dx + thumbWidth // 2 - 1] = (0, 192, 192)
    if thumbWidth // 2 >= 3:
        image[dy + 1, dx + thumbWidth // 2 - 2] = (0, 255, 255)
        image[dy + 1, dx + thumbWidth // 2 - 3] = (0, 255, 255)

# ---- THUMB DROP RIGHT ----
for i in range(num_thumb_drops):
    dx = end_x + 1 - i
    dy = finger_start_y + thumbDrop + 1 + i * 2
    cv2.rectangle(image, (dx, dy), (dx + thumbWidth // 2 - 1, dy + 1), (0, 0, 255), -1)
    image[dy + 1, dx] = (192, 192, 192)
    if thumbWidth // 2 >= 3:
        image[dy + 1, dx + 1] = (255, 255, 255)
        image[dy + 1, dx + 2] = (255, 255, 255)

# ---- SAVE OUTPUT ----
os.makedirs("images", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"Full_KnitGlove_{timestamp}.bmp"
filepath = os.path.join("images", filename)
cv2.imwrite(filepath, image)

print(f"Image saved to {filepath}")
