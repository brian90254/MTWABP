import cv2
import numpy as np
import argparse
from datetime import datetime
import os
import math

# Conversion ratios
palmWidthRatio = 1.696
palmHeightRatio = 2.261
wristHeightRatio = 1.391
castoffRow = 1
buffer = 1

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Create a parametric knit glove pattern BMP with ribbing and cables.")
parser.add_argument("lengthPalm", type=float, help="Palm length in arbitrary units")
parser.add_argument("circumferencePalm", type=float, help="Palm circumference in arbitrary units")
parser.add_argument("patternType", choices=["S", "B"], help="'S' for Snake, 'B' for Braided")
args = parser.parse_args()

# Rounding helpers
def round_to_nearest_even(value):
    rounded = int(round(value))
    return rounded if rounded % 2 == 0 else (rounded + 1 if rounded < value else rounded - 1)

def round_to_nearest_odd(value):
    rounded = int(round(value))
    return rounded if rounded % 2 != 0 else (rounded + 1 if rounded < value else rounded - 1)

# Raw computed values
raw_palmWidth = args.circumferencePalm * palmWidthRatio
raw_thumbWidth = raw_palmWidth / 4
raw_palmHeight = args.lengthPalm * palmHeightRatio
raw_wristHeight = args.lengthPalm * wristHeightRatio

# Apply rounding rules
palmWidth = round_to_nearest_odd(raw_palmWidth)
thumbWidth = round_to_nearest_even(raw_thumbWidth)
palmHeight = round_to_nearest_even(raw_palmHeight)
wristHeight = round_to_nearest_even(raw_wristHeight)
fingerRibHeight = round_to_nearest_odd(palmHeight / 3)
thumbDrop = round_to_nearest_even(0.4 * palmWidth)

# Final image dimensions
width = palmWidth + thumbWidth + buffer * 2
height = palmHeight + wristHeight + castoffRow + buffer * 2

# Create background image (gray)
image = np.full((height, width, 3), fill_value=192, dtype=np.uint8)

# === WRIST RIB KNIT ===
start_x = buffer + (thumbWidth // 2)
start_y = height - buffer - castoffRow - wristHeight + 1
end_x = start_x + palmWidth - 1
end_y = start_y + wristHeight - 1
cv2.rectangle(image, (start_x, start_y), (end_x, end_y), (0, 0, 255), thickness=-1)
colors = [(0, 0, 255), (0, 255, 0), (0, 255, 255), (255, 0, 0)]
for i in range(start_x, end_x + 1):
    image[end_y, i] = colors[(i - start_x) % len(colors)]
col_start_x = start_x + 3
col_end_x = end_x - 2
row_start_y = end_y - 3
row_end_y = start_y + 1
for x in range(col_start_x, col_end_x + 1, 2):
    for y in range(row_start_y, row_end_y - 1, -1):
        image[y, x] = (0, 255, 0)

# === FINGER RIB KNIT ===
finger_start_x = start_x
finger_end_x = finger_start_x + palmWidth - 1
finger_start_y = buffer + castoffRow
finger_end_y = finger_start_y + fingerRibHeight - 1
cv2.rectangle(image, (finger_start_x, finger_start_y), (finger_end_x, finger_end_y), (0, 0, 255), thickness=-1)
finger_col_start_x = finger_start_x + 3
finger_col_end_x = finger_end_x - 2
finger_row_start_y = finger_end_y - 1
finger_row_end_y = finger_start_y + 2
for x in range(finger_col_start_x, finger_col_end_x + 1, 2):
    for y in range(finger_row_start_y, finger_row_end_y - 1, -1):
        image[y, x] = (0, 255, 0)

# === PALM CABLE KNIT ===
palm_cable_width = palmWidth
palm_cable_height = palmHeight - fingerRibHeight
palm_cable_start_x = start_x
palm_cable_start_y = finger_end_y + 1
palm_cable_end_x = palm_cable_start_x + palm_cable_width - 1
palm_cable_end_y = palm_cable_start_y + palm_cable_height - 1
cv2.rectangle(image, (palm_cable_start_x, palm_cable_start_y), (palm_cable_end_x, palm_cable_end_y), (0, 0, 255), thickness=-1)
numberSnakeCables = math.floor(((palmWidth / 2) - 4) / 5)
numberBraidedCables = math.floor(((palmWidth / 2) - 4) / 7)

# Calculate the number of cable links
numberCableLinks = palm_cable_height // 4
isCableLinkOdd = (numberCableLinks % 2 != 0)


if args.patternType == "B":
    bx = palm_cable_start_x + 2
    by = palm_cable_start_y + 5
    mid_y = by + 1
    cv2.rectangle(image, (bx, by), (bx + 5, by + 2), (0, 0, 255), thickness=-1)
    image[mid_y, bx + 2] = (255, 0, 255)
    image[mid_y, bx + 3] = (255, 0, 255)
    image[mid_y, bx + 4] = (255, 255, 0)
    image[mid_y, bx + 5] = (255, 255, 0)
    bx2 = bx + 8
    cv2.rectangle(image, (bx2, by), (bx2 + 5, by + 2), (0, 0, 255), thickness=-1)
    image[mid_y, bx2 + 2] = (255, 0, 255)
    image[mid_y, bx2 + 3] = (255, 0, 255)
    image[mid_y, bx2 + 0] = (255, 255, 0)
    image[mid_y, bx2 + 1] = (255, 255, 0)

elif args.patternType == "S":
    sx = palm_cable_start_x + 2
    sy = palm_cable_start_y + 5
    mid_y = sy + 1
    cv2.rectangle(image, (sx, sy), (sx + 3, sy + 2), (0, 0, 255), thickness=-1)
    image[mid_y, sx + 0] = (255, 255, 0)
    image[mid_y, sx + 1] = (255, 255, 0)
    image[mid_y, sx + 2] = (255, 0, 255)
    image[mid_y, sx + 3] = (255, 0, 255)
    sx2 = sx + 6
    cv2.rectangle(image, (sx2, sy), (sx2 + 3, sy + 2), (0, 0, 255), thickness=-1)
    image[mid_y, sx2 + 0] = (255, 0, 255)
    image[mid_y, sx2 + 1] = (255, 0, 255)
    image[mid_y, sx2 + 2] = (255, 255, 0)
    image[mid_y, sx2 + 3] = (255, 255, 0)

# === THUMB DROP LEFT STACKED RECTANGLES ===
thumb_drop_width = thumbWidth // 2
thumb_drop_height = 2
num_thumb_drops = thumbWidth // 2

for i in range(num_thumb_drops):
    drop_x = finger_start_x - thumb_drop_width + i
    drop_y = finger_start_y + thumbDrop + i * 2
    end_x = drop_x + thumb_drop_width - 1
    end_y = drop_y + thumb_drop_height - 1
    cv2.rectangle(image, (drop_x, drop_y), (end_x, end_y), (0, 0, 255), thickness=-1)
    if end_x >= 0 and end_y >= 0:
        image[end_y, end_x] = (192, 192, 0)
        for j in range(1, 3):
            px = end_x - j
            if px >= 0:
                image[end_y, px] = (255, 255, 0)

# === THUMB DROP RIGHT STACKED RECTANGLES ===
for i in range(num_thumb_drops):
    drop_x = finger_end_x + 1 - i
    drop_y = finger_start_y + thumbDrop + 1 + i * 2
    end_x = drop_x + thumb_drop_width - 1
    end_y = drop_y + thumb_drop_height - 1
    cv2.rectangle(image, (drop_x, drop_y), (end_x, end_y), (0, 0, 255), thickness=-1)
    if end_x >= 0 and end_y >= 0:
        image[end_y, drop_x] = (192, 192, 192)
        for j in range(1, 3):
            px = drop_x + j
            if px <= end_x:
                image[end_y, px] = (255, 255, 255)

# === OUTPUT ===
os.makedirs("images", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"ParametricPattern_KnitGlove_{timestamp}.bmp"
filepath = os.path.join("images", filename)
cv2.imwrite(filepath, image)

print(f"Saved {filepath} with size {width}x{height}")
print(f"  palmWidth:        {palmWidth} (odd)")
print(f"  thumbWidth:       {thumbWidth} (even)")
print(f"  palmHeight:       {palmHeight} (even)")
print(f"  wristHeight:      {wristHeight} (even)")
print(f"  castoffRow:       {castoffRow} (added to image height)")
print(f"  fingerRibHeight:  {fingerRibHeight} (odd, not part of image size)")
print(f"  thumbDrop:        {thumbDrop} (even, based on 0.4 * palmWidth)")
print(f"  buffer:           {buffer}px on each side")
print(f"  Pattern type:     {'Snake' if args.patternType == 'S' else 'Braided'}")
print(f"  PALM CABLE KNIT:  red rect from ({palm_cable_start_x}, {palm_cable_start_y}) to ({palm_cable_end_x}, {palm_cable_end_y})")
print(f"    → Snake cables:   {numberSnakeCables}")
print(f"    → Braided cables: {numberBraidedCables}")
print(f"  THUMB DROP LEFT:  {num_thumb_drops} stacked rectangles")
print(f"  THUMB DROP RIGHT: {num_thumb_drops} stacked rectangles")
