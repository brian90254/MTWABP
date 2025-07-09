import cv2
import numpy as np
import argparse
from datetime import datetime
import os

# Conversion ratios
palmWidthRatio = 1.696
palmHeightRatio = 2.261
wristHeightRatio = 1.391
castoffRow = 1        # Extra row to add to height
buffer = 1            # Buffer pixels on each side

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Create a parametric knit glove pattern BMP with wrist/finger ribbing.")
parser.add_argument("lengthPalm", type=float, help="Palm length in arbitrary units")
parser.add_argument("circumferencePalm", type=float, help="Palm circumference in arbitrary units")
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

# New line here:
thumbDrop = round_to_nearest_even(0.4 * palmWidth)


# Final image dimensions
width = palmWidth + thumbWidth + buffer * 2
height = palmHeight + wristHeight + castoffRow + buffer * 2

# Create gray image background (BGR: 192, 192, 192)
image = np.full((height, width, 3), fill_value=192, dtype=np.uint8)

# === WRIST RIB KNIT SECTION ===
start_x = buffer + (thumbWidth // 2)
start_y = height - buffer - castoffRow - wristHeight + 1  # Shifted down by 1 pixel
end_x = start_x + palmWidth - 1
end_y = start_y + wristHeight - 1

# Draw solid red rectangle
cv2.rectangle(image, (start_x, start_y), (end_x, end_y), color=(0, 0, 255), thickness=-1)

# Color pattern on bottom row
colors = [(0, 0, 255), (0, 255, 0), (0, 255, 255), (255, 0, 0)]  # Red, Green, Yellow, Blue
for i in range(start_x, end_x + 1):
    image[end_y, i] = colors[(i - start_x) % len(colors)]

# Green columns inside WRIST rectangle
col_start_x = start_x + 3
col_end_x = end_x - 2
row_start_y = end_y - 3
row_end_y = start_y + 1
for x in range(col_start_x, col_end_x + 1, 2):
    for y in range(row_start_y, row_end_y - 1, -1):
        image[y, x] = (0, 255, 0)

# === FINGER RIB KNIT SECTION ===
finger_start_x = start_x
finger_end_x = finger_start_x + palmWidth - 1
finger_start_y = buffer + castoffRow
finger_end_y = finger_start_y + fingerRibHeight - 1

# Draw red rectangle for finger rib knit
cv2.rectangle(image, (finger_start_x, finger_start_y), (finger_end_x, finger_end_y), color=(0, 0, 255), thickness=-1)

# Green columns inside FINGER rectangle
finger_col_start_x = finger_start_x + 3
finger_col_end_x = finger_end_x - 2
finger_row_start_y = finger_end_y - 1
finger_row_end_y = finger_start_y + 2
for x in range(finger_col_start_x, finger_col_end_x + 1, 2):
    for y in range(finger_row_start_y, finger_row_end_y - 1, -1):
        image[y, x] = (0, 255, 0)

# # === THUMB DROP LEFT ===
# thumb_drop_width = thumbWidth // 2
# thumb_drop_height = 2

# thumb_drop_start_x = finger_start_x - thumb_drop_width
# thumb_drop_start_y = finger_start_y + thumbDrop
# thumb_drop_end_x = thumb_drop_start_x + thumb_drop_width - 1
# thumb_drop_end_y = thumb_drop_start_y + thumb_drop_height - 1

# # Draw red rectangle
# cv2.rectangle(image, 
#               (thumb_drop_start_x, thumb_drop_start_y), 
#               (thumb_drop_end_x, thumb_drop_end_y), 
#               color=(0, 0, 255), thickness=-1)

# # === CUSTOM COLORING: bottom right of THUMB DROP LEFT ===
# lower_y = thumb_drop_end_y
# rightmost_x = thumb_drop_end_x

# # Set the rightmost pixel to RGB (0, 192, 192) => BGR (192, 192, 0)
# if rightmost_x >= 0 and lower_y >= 0:
#     image[lower_y, rightmost_x] = (192, 192, 0)

# # Set the two pixels to the left to RGB (0, 255, 255) => BGR (255, 255, 0)
# for i in range(1, 3):
#     x = rightmost_x - i
#     if x >= 0:
#         image[lower_y, x] = (255, 255, 0)

# === THUMB DROP LEFT STACKED RECTANGLES ===
thumb_drop_width = thumbWidth // 2
thumb_drop_height = 2
num_thumb_drops = thumbWidth // 2

for i in range(num_thumb_drops):
    # Compute position for each stacked rectangle
    drop_x = finger_start_x - thumb_drop_width + i  # shift right by 1 each time
    drop_y = finger_start_y + thumbDrop + i * 2      # shift down by 2 each time
    end_x = drop_x + thumb_drop_width - 1
    end_y = drop_y + thumb_drop_height - 1

    # Draw red rectangle
    cv2.rectangle(image, (drop_x, drop_y), (end_x, end_y), color=(0, 0, 255), thickness=-1)

    # Add custom pixel colors on bottom row (y = end_y)
    if end_x >= 0 and end_y >= 0:
        image[end_y, end_x] = (192, 192, 0)  # RGB (0,192,192)
        for j in range(1, 3):
            px = end_x - j
            if px >= 0:
                image[end_y, px] = (255, 255, 0)  # RGB (0,255,255)

# === THUMB DROP RIGHT STACKED RECTANGLES ===
thumb_drop_width = thumbWidth // 2
thumb_drop_height = 2
num_thumb_drops = thumbWidth // 2

for i in range(num_thumb_drops):
    # Starting position: right of FINGER RIB, 1 pixel lower, shifting LEFT
    drop_x = finger_end_x + 1 - i            # shift left by 1 each time
    drop_y = finger_start_y + thumbDrop + 1 + i * 2  # 1px lower, +2px down per step
    end_x = drop_x + thumb_drop_width - 1
    end_y = drop_y + thumb_drop_height - 1

    # Draw red rectangle
    cv2.rectangle(image, (drop_x, drop_y), (end_x, end_y), color=(0, 0, 255), thickness=-1)

    # Custom pixel coloring on bottom row
    if end_x >= 0 and end_y >= 0:
        image[end_y, drop_x] = (192, 192, 192)  # RGB(192,192,192) → BGR
        for j in range(1, 3):
            px = drop_x + j
            if px <= end_x:
                image[end_y, px] = (255, 255, 255)  # RGB(255,255,255)




# Create output folder
output_folder = "images"
os.makedirs(output_folder, exist_ok=True)

# Save with timestamped filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"ParametricPattern_KnitGlove_{timestamp}.bmp"
filepath = os.path.join(output_folder, filename)
cv2.imwrite(filepath, image)

# Print report
print(f"Saved {filepath} with size {width}x{height}")
print(f"  palmWidth:        {palmWidth} (odd)")
print(f"  thumbWidth:       {thumbWidth} (even)")
print(f"  palmHeight:       {palmHeight} (even)")
print(f"  wristHeight:      {wristHeight} (even)")
print(f"  castoffRow:       {castoffRow} (added to image height)")
print(f"  fingerRibHeight:  {fingerRibHeight} (odd, not part of image size)")
print(f"  buffer:           {buffer}px on each side (total of {buffer*2}px added to width/height)")
print(f"  WRIST RIB KNIT:   red rect ({start_x},{start_y}) to ({end_x},{end_y})")
print(f"    → bottom row: repeating red, green, yellow, blue")
print(f"    → green cols: x={col_start_x} to {col_end_x}, y={row_start_y} to {row_end_y}")
print(f"  FINGER RIB KNIT:  red rect ({finger_start_x},{finger_start_y}) to ({finger_end_x},{finger_end_y})")
print(f"    → green cols: x={finger_col_start_x} to {finger_col_end_x}, y={finger_row_start_y} to {finger_row_end_y}")
