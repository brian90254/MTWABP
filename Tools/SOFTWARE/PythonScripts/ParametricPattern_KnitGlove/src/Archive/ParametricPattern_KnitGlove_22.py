# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SOFTWARE/PythonScripts/ParametricPattern_KnitGlove/
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/ParametricPattern_KnitGlove_19.py configs/BasicGlove_v40_LARGE_Rios.txt

import cv2
import numpy as np
from datetime import datetime
import os
import math
# FOR PRINTABLE VERSION
import sys

# ----------------------------
# LOAD CONFIG FROM FILE
# ----------------------------
def load_conversion_ratios(filepath):
    ratios = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                try:
                    ratios[key] = int(value)
                except ValueError:
                    try:
                        ratios[key] = float(value)
                    except ValueError:
                        ratios[key] = value
    return ratios

# Prompt user to choose a config file from the "configs" folder
configs_dir = "configs"
config_files = [f for f in os.listdir(configs_dir) if f.endswith(".txt")]

if not config_files:
    raise FileNotFoundError(f"No config files found in '{configs_dir}' folder.")

print("Select a configuration file:")
for idx, fname in enumerate(config_files):
    print(f"  {idx + 1}: {fname}")

selected_index = input("Enter the number of the config file to use: ").strip()
try:
    selected_index = int(selected_index)
    if not (1 <= selected_index <= len(config_files)):
        raise ValueError
except ValueError:
    raise ValueError("Invalid selection. Please enter a number from the list.")

selected_file = config_files[selected_index - 1]
selected_path = os.path.join(configs_dir, selected_file)

# Load all parameters
ratios = load_conversion_ratios(selected_path)

try:
    lengthPalm         = float(ratios["lengthPalm"])
    circumferencePalm  = float(ratios["circumferencePalm"])
    patternType        = str(ratios["patternType"]).strip().upper()
    handedness         = str(ratios["handedness"]).strip().upper()

    palmWidthRatio     = float(ratios["palmWidthRatio"])
    palmHeightRatio    = float(ratios["palmHeightRatio"])
    wristHeightRatio   = float(ratios["wristHeightRatio"])
    thumbDropRatio     = float(ratios["thumbDropRatio"])
    thumbHeightRatio   = float(ratios["thumbHeightRatio"])
    thumbWidening      = str(ratios["thumbWidening"]).strip().upper()
    fingerHeightRatio  = float(ratios["fingerHeightRatio"])
    castoffRow         = int(ratios["castoffRow"])
    buffer             = int(ratios["buffer"])

except KeyError as e:
    raise ValueError(f"Missing required parameter in {args.ratiosFile}: {e}")


# Rounding helpers
def round_to_nearest_even(value):
    rounded = int(round(value))
    return rounded if rounded % 2 == 0 else (rounded + 1 if rounded < value else rounded - 1)

def round_to_nearest_odd(value):
    rounded = int(round(value))
    return rounded if rounded % 2 != 0 else (rounded + 1 if rounded < value else rounded - 1)

# Raw computed values
raw_palmWidth = circumferencePalm * palmWidthRatio
raw_thumbWidth = raw_palmWidth / 4
raw_palmHeight = lengthPalm * palmHeightRatio
raw_wristHeight = lengthPalm * wristHeightRatio

# Apply rounding rules
palmWidth = round_to_nearest_odd(raw_palmWidth)
thumbWidth = round_to_nearest_even(raw_thumbWidth)
palmHeight = round_to_nearest_even(raw_palmHeight)
wristHeight = round_to_nearest_even(raw_wristHeight)
fingerRibHeight = round_to_nearest_odd(palmHeight / fingerHeightRatio)
thumbDrop = round_to_nearest_even(thumbDropRatio * palmWidth)

# Final image dimensions
width = palmWidth + thumbWidth + buffer * 2
height = palmHeight + wristHeight + castoffRow + buffer * 2

# Create background image (gray)
image = np.full((height, width, 3), fill_value=224, dtype=np.uint8)

# ----------------------
# === WRIST JERSEY SECTION (NO RIB YET, JUST FILL)===
start_x = buffer + (thumbWidth // 2)
start_y = height - buffer - castoffRow - wristHeight + 1
end_x = start_x + palmWidth - 1
end_y = start_y + wristHeight - 1
cv2.rectangle(image, (start_x, start_y), (end_x, end_y), (128, 128, 255), thickness=-1)

# ----------------------
# === FINGER RIB KNIT SECTION ===
start_x = buffer + (thumbWidth // 2)
finger_start_x = start_x
finger_end_x = finger_start_x + palmWidth - 1
finger_start_y = buffer + castoffRow
finger_end_y = finger_start_y + fingerRibHeight - 1
cv2.rectangle(image, (finger_start_x, finger_start_y), (finger_end_x, finger_end_y), (128, 128, 255), thickness=-1)
finger_col_start_x = finger_start_x + 3
finger_col_end_x = finger_end_x - 2
finger_row_start_y = finger_end_y - 1
finger_row_end_y = finger_start_y + 2
for x in range(finger_col_start_x, finger_col_end_x + 1, 2):
    for y in range(finger_row_start_y, finger_row_end_y - 1, -1):
        image[y, x] = (0, 255, 0)

# ----------------------
# === PALM JERSEY KNIT SECTION ===
palm_cable_width = palmWidth
palm_cable_height = palmHeight - fingerRibHeight
palm_cable_start_x = start_x
palm_cable_start_y = finger_end_y + 1
palm_cable_end_x = palm_cable_start_x + palm_cable_width - 1
palm_cable_end_y = palm_cable_start_y + palm_cable_height - 1
cv2.rectangle(image, (palm_cable_start_x, palm_cable_start_y), (palm_cable_end_x, palm_cable_end_y), (128, 128, 255), thickness=-1)
# TWO BY TWO CABLES == 2 + 2 + 1 for offset = 5
numberSnakeCables = math.floor(((palmWidth / 2) - 4) / 5)
numberTwoByTwoCables = math.floor(((palmWidth / 2) - 4) / 5)
# THREE BY TWO CABLES == 2 + 2 + 2 + 1 for offset = 7
numberBraidedCables = math.floor(((palmWidth / 2) - 4) / 7)
# TWO BY THREE CABLES == 3 + 3 + 1 for offset = 7
numberTwoByThreeCables = math.floor(((palmWidth / 2) - 4) / 7)


# ----------------------
# === THUMB DROP LEFT & RIGHT (simplified calc) ===
thumb_drop_width = thumbWidth // 2
thumb_drop_height = 2
thumbHeight = int(thumbWidth / thumbHeightRatio)
num_thumb_drops = int((thumbWidth // 2) + thumbHeight)

# ----------------------
# === THUMB DROP LEFT STACKED RECTANGLES ===
# ----------------------
for i in range(num_thumb_drops):
    drop_y = finger_start_y + thumbDrop + i * 2
    end_y = drop_y + thumb_drop_height - 1
    if i > (thumbHeight - 1) :
        drop_x = finger_start_x - thumb_drop_width + (i - thumbHeight)
        end_x = drop_x + thumb_drop_width - 1
    else:
        drop_x = finger_start_x - thumb_drop_width
        end_x = drop_x + thumb_drop_width - 1
    cv2.rectangle(image, (drop_x, drop_y), (end_x, end_y), (128, 128, 255), thickness=-1)
    
    if i > (thumbHeight - 1):
        if end_x >= 0 and end_y >= 0:
            center_x = drop_x + (thumb_drop_width // 2)
            if center_x <= end_x:
                #if patternType == "C3":
                if thumbWidening == "W3":
                    image[end_y, center_x + 1] = (192, 192, 0)  # dark cyan center pixel
                    for j in range(1, 4):  # cyan pixels to the left
                        px = center_x - j + 1
                        if px <= end_x:
                            image[end_y, px] = (255, 255, 0)
                else:
                    image[end_y, center_x] = (192, 192, 0)  # grey center pixel
                    for j in range(1, 3):  # cyan pixels to the left
                        px = center_x - j
                        if px <= end_x:
                            image[end_y, px] = (255, 255, 0)

# ----------------------
# === THUMB DROP RIGHT STACKED RECTANGLES ===
# ----------------------
for i in range(num_thumb_drops):
    drop_y = finger_start_y + thumbDrop + 1 + i * 2
    end_y = drop_y + thumb_drop_height - 1
    if i > (thumbHeight - 1) :
        drop_x = finger_end_x + 1 - (i - thumbHeight)
        end_x = drop_x + thumb_drop_width - 1
    else:
        drop_x = finger_end_x + 1
        end_x = drop_x + thumb_drop_width - 1
    cv2.rectangle(image, (drop_x, drop_y), (end_x, end_y), (128, 128, 255), thickness=-1)
    
    if i > (thumbHeight - 1):
        if end_x >= 0 and end_y >= 0:
            center_x = drop_x + (thumb_drop_width // 2)
            if center_x <= end_x:
                #if patternType == "C3":
                if thumbWidening == "W3":
                    image[end_y, center_x - 1] = (160, 160, 160)  # grey center pixel
                    for j in range(1, 4):  # white pixels to the right
                        px = center_x + j - 1
                        if px <= end_x:
                            image[end_y, px] = (255, 255, 255)
                else:
                    image[end_y, center_x] = (160, 160, 160)  # grey center pixel
                    for j in range(1, 3):  # white pixels to the right
                        px = center_x + j
                        if px <= end_x:
                            image[end_y, px] = (255, 255, 255)


# === WRIST RIB KNIT SECTION ===
start_x = buffer + (thumbWidth // 2)
start_y = height - buffer - castoffRow - wristHeight + 1
end_x = start_x + palmWidth - 1
end_y = start_y + wristHeight - 1
#cv2.rectangle(image, (start_x, start_y), (end_x, end_y), (128, 128, 255), thickness=-1)
colors = [(128, 128, 255), (0, 255, 0), (0, 255, 255), (255, 0, 0)]
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
# === PALM CABLE KNIT ===
# ----------------------
# Calculate the number of cable links
center_y = palm_cable_start_y + palm_cable_height // 2
# numberCableLinks = palm_cable_height // 4
numberCableLinks = palm_cable_height // (6 if patternType == "C3" else 4)
isCableLinkOdd = (numberCableLinks % 2 != 0)
print(f"isCableLinkOdd = {isCableLinkOdd}")

braided_w, braided_h = 6, 3
snake_w, snake_h = 4, 3
start_offset_x = 5

# NUMBER OF CABLES
if patternType == "B":
    numCables = numberBraidedCables
elif patternType == "S":
    numCables = numberSnakeCables
elif patternType == "C2":
    numCables = numberTwoByTwoCables
elif patternType == "C3":
    numCables = numberTwoByThreeCables
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

lookupTableEvenLeftX3 = {
    0: -3,
    3: 9,
    4: -15,
    7: 21,
    8: -27,
    11: 33,
    12: -39,
    15: 45,
    16: -51,
    19: 57,
    20: -63,
    # intentionally skipping other keys
}

lookupTableEvenRightX3 = {
    1: 3,
    2: -9,
    5: 15,
    6: -21,
    9: 27,
    10: -33,
    13: 39,
    14: -45,
    17: 51,
    18: -57,
    21: 63,
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

lookupTableOddLeftX3 = {
    0: 0,
    3: 12,
    4: -12,
    7: 24,
    8: -24,
    11: 36,
    12: -36,
    15: 48,
    16: -48,
    19: 60,
    20: -60
    # intentionally skipping other keys
}

lookupTableOddRightX3 = {
    1: 6,
    2: -6,
    5: 18,
    6: -18,
    9: 30,
    10: -30,
    13: 42,
    14: -42,
    17: 54,
    18: -54,
    # intentionally skipping other keys
}

cable_x = start_x + start_offset_x
image[palm_cable_start_y:palm_cable_end_y + 1, cable_x] = (0, 255, 0)

for i in range(numCables):
    # print(f"numCable = {i}")
    #cable_x = start_x + start_offset_x + (i * ((braided_w + 1) if patternType == "B" else (snake_w + 1)))
    cable_x = start_x + start_offset_x + (i * ((braided_w + 1) if patternType in ("B", "C3") else (snake_w + 1)))
    if not isCableLinkOdd:
        # print(f"isCableLinkOdd = {isCableLinkOdd}")
        if patternType == "B":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeft.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        # image[ry + 1, cable_x + 5] = (255, 0, 0)
                        # image[ry + 1, cable_x + 6] = (255, 0, 0)

        elif patternType == "S":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeft.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (128, 128, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                    # ---------------------
                    # EVEN RIGHT
                    offsetEvenRight = lookupTableEvenRight.get(j,None)
                    if offsetEvenRight is not None:
                        ry = center_y + offsetEvenRight - 1
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (128, 128, 255), -1)
                        # ODD SWAPS LEFT AND RIGHT
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)


        elif patternType == "C3":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeftX3.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 255)
                        image[ly + 1, cable_x + 2] = (255, 0, 255)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 0)
                        image[ly + 1, cable_x + 5] = (255, 0, 0)
                        image[ly + 1, cable_x + 6] = (255, 0, 0)
                    # ---------------------
                    # EVEN RIGHT
                    offsetEvenRight = lookupTableEvenRightX3.get(j,None)
                    if offsetEvenRight is not None:
                        ry = center_y + offsetEvenRight - 1
                        # ---------------------
                        # EVEN LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 255)
                        image[ry + 1, cable_x + 2] = (255, 0, 255)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 0)
                        image[ry + 1, cable_x + 5] = (255, 0, 0)
                        image[ry + 1, cable_x + 6] = (255, 0, 0)
            
            else:
                # i is odd
                print(f"{i} is odd")
                for j in range(numberCableLinks):
                    # ---------------------
                    # EVEN LEFT
                    offsetEvenLeft = lookupTableEvenLeftX3.get(j,None)
                    if offsetEvenLeft is not None:
                        ly = center_y + offsetEvenLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 0)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                        image[ly + 1, cable_x + 5] = (255, 0, 255)
                        image[ly + 1, cable_x + 6] = (255, 0, 255)
                    # ---------------------
                    # EVEN RIGHT
                    offsetEvenRight = lookupTableEvenRightX3.get(j,None)
                    if offsetEvenRight is not None:
                        ry = center_y + offsetEvenRight - 1
                        # ---------------------
                        # EVEN LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 0)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        image[ry + 1, cable_x + 5] = (255, 0, 255)
                        image[ry + 1, cable_x + 6] = (255, 0, 255)

    else:
        # print(f"isCableLinkOdd = {isCableLinkOdd}")
        if patternType == "B":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeft.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        # image[ry + 1, cable_x + 5] = (255, 0, 0)
                        # image[ry + 1, cable_x + 6] = (255, 0, 0)

        elif patternType == "S":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeft.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (128, 128, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                    # ---------------------
                    # Odd RIGHT
                    offsetOddRight = lookupTableOddRight.get(j,None)
                    if offsetOddRight is not None:
                        ry = center_y + offsetOddRight - 1
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + snake_w, ly + snake_h - 1), (128, 128, 255), -1)
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
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + snake_w, ry + snake_h - 1), (128, 128, 255), -1)
                        # ODD SWAPS LEFT AND RIGHT
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)

        elif patternType == "C3":
            if i % 2 == 0:
                # i is even
                print(f"{i} is even")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeftX3.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 255)
                        image[ly + 1, cable_x + 2] = (255, 0, 255)
                        image[ly + 1, cable_x + 3] = (255, 0, 255)
                        image[ly + 1, cable_x + 4] = (255, 0, 0)
                        image[ly + 1, cable_x + 5] = (255, 0, 0)
                        image[ly + 1, cable_x + 6] = (255, 0, 0)
                    # ---------------------
                    # Odd RIGHT
                    offsetOddRight = lookupTableOddRightX3.get(j,None)
                    if offsetOddRight is not None:
                        ry = center_y + offsetOddRight - 1
                        # ---------------------
                        # Odd LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 255)
                        image[ry + 1, cable_x + 2] = (255, 0, 255)
                        image[ry + 1, cable_x + 3] = (255, 0, 255)
                        image[ry + 1, cable_x + 4] = (255, 0, 0)
                        image[ry + 1, cable_x + 5] = (255, 0, 0)
                        image[ry + 1, cable_x + 6] = (255, 0, 0)
            
            else:
                # i is odd
                print(f"{i} is odd")
                for j in range(numberCableLinks):
                    # ---------------------
                    # Odd LEFT
                    offsetOddLeft = lookupTableOddLeftX3.get(j,None)
                    if offsetOddLeft is not None:
                        ly = center_y + offsetOddLeft - 1
                        cv2.rectangle(image, (cable_x + 1, ly), (cable_x + braided_w, ly + braided_h - 1), (128, 128, 255), -1)
                        image[ly + 1, cable_x + 1] = (255, 0, 0)
                        image[ly + 1, cable_x + 2] = (255, 0, 0)
                        image[ly + 1, cable_x + 3] = (255, 0, 0)
                        image[ly + 1, cable_x + 4] = (255, 0, 255)
                        image[ly + 1, cable_x + 5] = (255, 0, 255)
                        image[ly + 1, cable_x + 6] = (255, 0, 255)
                    # ---------------------
                    # Odd RIGHT
                    offsetOddRight = lookupTableOddRightX3.get(j,None)
                    if offsetOddRight is not None:
                        ry = center_y + offsetOddRight - 1
                        # ---------------------
                        # Odd LEFT
                        cv2.rectangle(image, (cable_x + 1, ry), (cable_x + braided_w, ry + braided_h - 1), (128, 128, 255), -1)
                        image[ry + 1, cable_x + 1] = (255, 0, 0)
                        image[ry + 1, cable_x + 2] = (255, 0, 0)
                        image[ry + 1, cable_x + 3] = (255, 0, 0)
                        image[ry + 1, cable_x + 4] = (255, 0, 255)
                        image[ry + 1, cable_x + 5] = (255, 0, 255)
                        image[ry + 1, cable_x + 6] = (255, 0, 255)
                        

    #cable_right_x = cable_x + ((braided_w + 1) if patternType == "B" else (snake_w + 1))
    cable_right_x = cable_x + ((braided_w + 1) if patternType in ("B", "C3") else (snake_w + 1))
    image[palm_cable_start_y:palm_cable_end_y + 1, cable_right_x] = (0, 255, 0)


# === MIRROR PALM SECTION (LEFT HAND ONLY) ===
if handedness == 'L':
    #left_inner_x = start_x + 3
    left_inner_x = start_x + 4
    right_inner_x = end_x - 4
    bottom_y = start_y - 1
    top_y = finger_end_y + 1
    region = image[top_y:bottom_y + 1, left_inner_x:right_inner_x + 1]
    mirrored = cv2.flip(region, 1)
    if mirrored.size > 0:
        image[top_y:bottom_y + 1, left_inner_x:right_inner_x + 1] = mirrored



# === OUTPUT ===
os.makedirs("images", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"ParametricPattern_KnitGlove_{timestamp}_Cable{patternType}_{handedness}.bmp"
filepath = os.path.join("images", filename)
cv2.imwrite(filepath, image)

print(f"Saved {filepath} with size {width}x{height}")
print(f"  palmWidth:        {palmWidth} (odd)")
print(f"  thumbWidth:       {thumbWidth} (even)")
print(f"  palmHeight:       {palmHeight} (even)")
print(f"  wristHeight:      {wristHeight} (even)")
print(f"  castoffRow:       {castoffRow} (added to image height)")
print(f"  fingerRibHeight:  {fingerRibHeight} (odd, not part of image size)")
print(f"  thumbDrop:        {thumbDrop} (even)")
print(f"  buffer:           {buffer}px")
print(f"  Pattern type:     {'Snake' if patternType == 'S' else 'Braided'}")
print(f"    → Snake cables:   {numberSnakeCables}")
print(f"    → Braided cables: {numberBraidedCables}")
print(f"  THUMB DROP:       {num_thumb_drops} stacked rectangles")


# ----------------------------------------------------------------
#   CREATE PRINTABLE VERSION :: MERGED CODE
# ----------------------------------------------------------------
# Automatically generate output path by changing extension to .png
#output_path = os.path.splitext(input_path)[0] + '.png'
input_path = f"images/ParametricPattern_KnitGlove_{timestamp}_Cable{patternType}_{handedness}.bmp"
output_path = f"images/ParametricPattern_KnitGlove_{timestamp}_Cable{patternType}_{handedness}.png"

# === CONFIGURATION ===
scale_factor = 100
border_color = (0, 0, 0)  # black border
default_text_color = (0, 0, 0)  # black text
font = cv2.FONT_HERSHEY_SIMPLEX
default_font_scale = 2
font_thickness = 3

# === COLOR TO TEXT MAPPING (BGR format for OpenCV) ===
color_text_map = {
    (255, 255, 0): "6",
    (255, 0, 255): "5",
    (255, 255, 255): "7",
    (255, 0, 0): "4",
    (192, 192, 0): "106",
    (160, 160, 160): "107",
    (128, 128, 255): "1",
    (0, 255, 0): "2",
    (0, 255, 255): "3",
}

# === LOAD BMP IMAGE ===
image = cv2.imread(input_path, cv2.IMREAD_COLOR)
if image is None:
    raise ValueError(f"Could not load image: {input_path}")

height, width, _ = image.shape
scaled_height = height * scale_factor
scaled_width = width * scale_factor

# === CREATE NEW SCALED IMAGE ===
scaled_image = np.zeros((scaled_height, scaled_width, 3), dtype=np.uint8)

# === SCALE AND DRAW BLOCKS ===
for y in range(height):
    for x in range(width):
        color = tuple(int(c) for c in image[y, x])
        top_left_x = x * scale_factor
        top_left_y = y * scale_factor
        bottom_right_x = top_left_x + scale_factor - 1
        bottom_right_y = top_left_y + scale_factor - 1

        # Fill block
        cv2.rectangle(scaled_image, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), color, -1)

        # Draw border
        cv2.rectangle(scaled_image, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), border_color, 1)

        # Annotate with text
        if color in color_text_map:
            text = color_text_map[color]
            font_scale = 1.5 if text in ["106", "107"] else default_font_scale
            text_color = (255, 255, 255) if text == "4" else default_text_color
            text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
            text_width, text_height = text_size
            text_x = top_left_x + (scale_factor - text_width) // 2
            text_y = top_left_y + (scale_factor + text_height) // 2
            cv2.putText(scaled_image, text, (text_x, text_y), font, font_scale, text_color, font_thickness, cv2.LINE_AA)

# === ADD ROW AND COLUMN NUMBERS ===
number_font_scale = 1.2
number_font_thickness = 2
number_color = (0, 0, 0)

for x in range(width):
    col_number = str(x)
    text_size, _ = cv2.getTextSize(col_number, font, number_font_scale, number_font_thickness)
    text_width, text_height = text_size
    x_center = x * scale_factor + (scale_factor - text_width) // 2
    cv2.putText(scaled_image, col_number, (x_center, text_height + 5), font, number_font_scale, number_color, number_font_thickness, cv2.LINE_AA)
    bottom_y = scaled_height - 5
    cv2.putText(scaled_image, col_number, (x_center, bottom_y), font, number_font_scale, number_color, number_font_thickness, cv2.LINE_AA)

for y in range(height):
    row_number = str(height - 1 - y)
    text_size, _ = cv2.getTextSize(row_number, font, number_font_scale, number_font_thickness)
    text_width, text_height = text_size
    y_center = y * scale_factor + (scale_factor + text_height) // 2
    cv2.putText(scaled_image, row_number, (5, y_center), font, number_font_scale, number_color, number_font_thickness, cv2.LINE_AA)
    right_x = scaled_width - text_width - 5
    cv2.putText(scaled_image, row_number, (right_x, y_center), font, number_font_scale, number_color, number_font_thickness, cv2.LINE_AA)

# === SAVE THE OUTPUT IMAGE ===
cv2.imwrite(output_path, scaled_image)
print(f"Saved scaled image to {output_path}")

