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
image = np.full((height, width, 3), fill_value=224, dtype=np.uint8)

# ----------------------
# === WRIST RIB KNIT ===
# ----------------------
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

# ----------------------
# === FINGER RIB KNIT ===
# ----------------------
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

# ----------------------
# === PALM CABLE KNIT ===
# ----------------------
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
center_y = palm_cable_start_y + palm_cable_height // 2
numberCableLinks = palm_cable_height // 4
isCableLinkOdd = (numberCableLinks % 2 != 0)
print(f"isCableLinkOdd = {isCableLinkOdd}")

braided_w, braided_h = 6, 3
snake_w, snake_h = 4, 3
start_offset_x = 5

# NUMBER OF CABLES
if args.patternType == "B":
    numCables = numberBraidedCables
elif args.patternType == "S":
    numCables = numberSnakeCables
else:
    numCables = 0

# ----------------------
# LOOKUP TABLES
# ----------------------
lookupTableEvenLeft = {
    0: -2,
    3: 6,
    4: -10,
    7: 14,
    8: -18,
    11: 22,
    12: -26,
    15: 30,
    16: -34,
    19: 38,
    20: -42
    # intentionally skipping other keys
}

lookupTableEvenRight = {
    1: 2,
    2: -6,
    5: 10,
    6: -14,
    9: 18,
    10: -22,
    13: 26,
    14: -30,
    17: 34,
    18: -38,
    # intentionally skipping other keys
}

lookupTableOddLeft = {
    0: 0,
    3: 8,
    4: -8,
    7: 16,
    8: -16,
    11: 24,
    12: -24,
    15: 32,
    16: -32,
    19: 40,
    20: -40
    # intentionally skipping other keys
}

lookupTableOddRight = {
    1: 4,
    2: -4,
    5: 12,
    6: -12,
    9: 20,
    10: -20,
    13: 28,
    14: -28,
    17: 36,
    18: -36,
    # intentionally skipping other keys
}

cable_x = start_x + start_offset_x
image[palm_cable_start_y:palm_cable_end_y + 1, cable_x] = (0, 255, 0)

for i in range(numCables):
    # print(f"numCable = {i}")
    cable_x = start_x + start_offset_x + (i * ((braided_w + 1) if args.patternType == "B" else (snake_w + 1)))

    if not isCableLinkOdd:
        # print(f"isCableLinkOdd = {isCableLinkOdd}")
        if args.patternType == "B":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeft.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (0, 0, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                        # image[ry + 1, cable_x + 5] = (255, 0, 0)
                        # image[ry + 1, cable_x + 6] = (255, 0, 0)
                    # ---------------------
                    # EVEN RIGHT
                    offsetEvenRight = lookupTableEvenRight.get(j,None)
                    if offsetEvenRight is not None:
                        ry = center_y + offsetEvenRight - 1
                        # ---------------------
                        # EVEN LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (0, 0, 255), -1)
                        # image[ly + 1, cable_x + 1] = (255, 0, 0)
                        # image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        image[ry + 1, cable_x + 5] = (255, 0, 0)
                        image[ry + 1, cable_x + 6] = (255, 0, 0)
            
            else:
                # i is odd
                print(f"{i} is odd")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeft.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (0, 0, 255), -1)
                        # image[ly + 1, cable_x + 1] = (255, 0, 0)
                        # image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                        image[ly + 1, cable_x + 5] = (255, 0, 0)
                        image[ly + 1, cable_x + 6] = (255, 0, 0)
                    # ---------------------
                    # EVEN RIGHT
                    offsetEvenRight = lookupTableEvenRight.get(j,None)
                    if offsetEvenRight is not None:
                        ry = center_y + offsetEvenRight - 1
                        # ---------------------
                        # EVEN LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (0, 0, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        # image[ry + 1, cable_x + 5] = (255, 0, 0)
                        # image[ry + 1, cable_x + 6] = (255, 0, 0)


        elif args.patternType == "S":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeft.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (0, 0, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                    # ---------------------
                    # EVEN RIGHT
                    offsetEvenRight = lookupTableEvenRight.get(j,None)
                    if offsetEvenRight is not None:
                        ry = center_y + offsetEvenRight - 1
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (0, 0, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 255)
                        image[ry + 1, cable_x + 2] = (255, 0, 255)
                        image[ry + 1, cable_x + 3] = (255, 0, 0)
                        image[ry + 1, cable_x + 4] = (255, 0, 0)

            else:
                # i is odd
                print(f"{i} is odd")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeft.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (0, 0, 255), -1)
                        # ODD SWAPS LEFT AND RIGHT
                        image[ly + 1, cable_x + 1] = (255, 0, 255)
                        image[ly + 1, cable_x + 2] = (255, 0, 255)
                        image[ly + 1, cable_x + 3] = (255, 0, 0)
                        image[ly + 1, cable_x + 4] = (255, 0, 0)
                    # ---------------------
                    # EVEN RIGHT
                    offsetEvenRight = lookupTableEvenRight.get(j,None)
                    if offsetEvenRight is not None:
                        ry = center_y + offsetEvenRight - 1
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (0, 0, 255), -1)
                        # ODD SWAPS LEFT AND RIGHT
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)

    else:
        # print(f"isCableLinkOdd = {isCableLinkOdd}")
        if args.patternType == "B":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeft.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (0, 0, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                        # image[ry + 1, cable_x + 5] = (255, 0, 0)
                        # image[ry + 1, cable_x + 6] = (255, 0, 0)
                    # ---------------------
                    # Odd RIGHT
                    offsetOddRight = lookupTableOddRight.get(j,None)
                    if offsetOddRight is not None:
                        ry = center_y + offsetOddRight - 1
                        # ---------------------
                        # Odd LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (0, 0, 255), -1)
                        # image[ly + 1, cable_x + 1] = (255, 0, 0)
                        # image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        image[ry + 1, cable_x + 5] = (255, 0, 0)
                        image[ry + 1, cable_x + 6] = (255, 0, 0)
            
            else:
                # i is odd
                print(f"{i} is odd")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeft.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (0, 0, 255), -1)
                        # image[ly + 1, cable_x + 1] = (255, 0, 0)
                        # image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                        image[ly + 1, cable_x + 5] = (255, 0, 0)
                        image[ly + 1, cable_x + 6] = (255, 0, 0)
                    # ---------------------
                    # Odd RIGHT
                    offsetOddRight = lookupTableOddRight.get(j,None)
                    if offsetOddRight is not None:
                        ry = center_y + offsetOddRight - 1
                        # ---------------------
                        # Odd LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (0, 0, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        # image[ry + 1, cable_x + 5] = (255, 0, 0)
                        # image[ry + 1, cable_x + 6] = (255, 0, 0)


        elif args.patternType == "S":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeft.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (0, 0, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                    # ---------------------
                    # Odd RIGHT
                    offsetOddRight = lookupTableOddRight.get(j,None)
                    if offsetOddRight is not None:
                        ry = center_y + offsetOddRight - 1
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (0, 0, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 255)
                        image[ry + 1, cable_x + 2] = (255, 0, 255)
                        image[ry + 1, cable_x + 3] = (255, 0, 0)
                        image[ry + 1, cable_x + 4] = (255, 0, 0)

            else:
                # i is odd
                print(f"{i} is odd")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeft.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (0, 0, 255), -1)
                        # ODD SWAPS LEFT AND RIGHT
                        image[ly + 1, cable_x + 1] = (255, 0, 255)
                        image[ly + 1, cable_x + 2] = (255, 0, 255)
                        image[ly + 1, cable_x + 3] = (255, 0, 0)
                        image[ly + 1, cable_x + 4] = (255, 0, 0)
                    # ---------------------
                    # Odd RIGHT
                    offsetOddRight = lookupTableOddRight.get(j,None)
                    if offsetOddRight is not None:
                        ry = center_y + offsetOddRight - 1
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (0, 0, 255), -1)
                        # ODD SWAPS LEFT AND RIGHT
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)

    cable_right_x = cable_x + ((braided_w + 1) if args.patternType == "B" else (snake_w + 1))
    image[palm_cable_start_y:palm_cable_end_y + 1, cable_right_x] = (0, 255, 0)


# ----------------------
# === THUMB DROP LEFT STACKED RECTANGLES ===
# ----------------------
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
        center_x = drop_x + (thumb_drop_width // 2)
        if center_x <= end_x:
            image[end_y, center_x] = (192, 192, 0)  # grey center pixel
            for j in range(1, 3):  # white pixels to the right
                px = center_x - j
                if px <= end_x:
                    image[end_y, px] = (255, 255, 0)

# ----------------------
# === THUMB DROP RIGHT STACKED RECTANGLES ===
# ----------------------
for i in range(num_thumb_drops):
    drop_x = finger_end_x + 1 - i
    drop_y = finger_start_y + thumbDrop + 1 + i * 2
    end_x = drop_x + thumb_drop_width - 1
    end_y = drop_y + thumb_drop_height - 1
    cv2.rectangle(image, (drop_x, drop_y), (end_x, end_y), (0, 0, 255), thickness=-1)
    
    if end_x >= 0 and end_y >= 0:
        center_x = drop_x + (thumb_drop_width // 2)
        if center_x <= end_x:
            image[end_y, center_x] = (160, 160, 160)  # grey center pixel
            for j in range(1, 3):  # white pixels to the right
                px = center_x + j
                if px <= end_x:
                    image[end_y, px] = (255, 255, 255)

# ----------------------
# === OUTPUT ===
# ----------------------
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
