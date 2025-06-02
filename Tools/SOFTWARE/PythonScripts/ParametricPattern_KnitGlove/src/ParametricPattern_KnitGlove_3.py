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
parser = argparse.ArgumentParser(description="Create a parametric knit glove pattern BMP with color pattern in WRIST RIB KNIT.")
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

# Derived value (not part of image size)
fingerRibHeight = round_to_nearest_odd(palmHeight / 3)

# Final image dimensions
width = palmWidth + thumbWidth + buffer * 2
height = palmHeight + wristHeight + castoffRow + buffer * 2

# Create gray image background (BGR: 192, 192, 192)
image = np.full((height, width, 3), fill_value=192, dtype=np.uint8)

# === WRIST RIB KNIT SECTION ===
# Calculate rectangle top-left and bottom-right coordinates
start_x = buffer + (thumbWidth // 2)
start_y = height - buffer - castoffRow - wristHeight
end_x = start_x + palmWidth - 1
end_y = start_y + wristHeight - 1

# Draw solid red rectangle
cv2.rectangle(image, (start_x, start_y), (end_x, end_y), color=(0, 0, 255), thickness=-1)

# Draw color pattern on bottom row of the rectangle
colors = [
    (0, 0, 255),     # Red
    (0, 255, 0),     # Green
    (0, 255, 255),   # Yellow
    (255, 0, 0)      # Blue
]

for i in range(start_x, end_x + 1):
    color_index = (i - start_x) % len(colors)
    image[end_y, i] = colors[color_index]

# Draw color pattern on bottom row of the rectangle
for i in range(start_x, end_x + 1):
    color_index = (i - start_x) % len(colors)
    image[end_y, i] = colors[color_index]

# Draw vertical green columns inside the rectangle
column_start_x = start_x + 3
column_end_x = end_x - 2
row_start_y = end_y - 3
row_end_y = start_y + 1

for x in range(column_start_x, column_end_x + 1, 2):
    for y in range(row_start_y, row_end_y - 1, -1):
        image[y, x] = (0, 255, 0)  # Green

# === FINGER RIB KNIT SECTION ===
finger_start_x = start_x  # Same horizontal position as wrist rib
finger_end_x = finger_start_x + palmWidth - 1
finger_start_y = buffer + castoffRow
finger_end_y = finger_start_y + fingerRibHeight - 1

# Draw red rectangle for finger rib knit
cv2.rectangle(image, (finger_start_x, finger_start_y), (finger_end_x, finger_end_y), color=(0, 0, 255), thickness=-1)

# Draw vertical green columns in FINGER RIB KNIT section
finger_col_start_x = finger_start_x + 3
finger_col_end_x = finger_end_x - 2
finger_row_start_y = finger_end_y - 1
finger_row_end_y = finger_start_y + 2

for x in range(finger_col_start_x, finger_col_end_x + 1, 2):
    for y in range(finger_row_start_y, finger_row_end_y - 1, -1):
        image[y, x] = (0, 255, 0)  # Green


# Create output folder if it doesn't exist
output_folder = "images"
os.makedirs(output_folder, exist_ok=True)

# Generate timestamped filename and full path
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"ParametricPattern_KnitGlove_{timestamp}.bmp"
filepath = os.path.join(output_folder, filename)

# Save the image
cv2.imwrite(filepath, image)

# Calculate actual drawn rectangle size
knit_rect_width = end_x - start_x + 1
knit_rect_height = end_y - start_y + 1

# Print report
print(f"Saved {filepath} with size {width}x{height}")
print(f"  palmWidth:        {palmWidth} (odd)")
print(f"  thumbWidth:       {thumbWidth} (even)")
print(f"  palmHeight:       {palmHeight} (even)")
print(f"  wristHeight:      {wristHeight} (even)")
print(f"  castoffRow:       {castoffRow} (added to image height)")
print(f"  fingerRibHeight:  {fingerRibHeight} (odd, not part of image)")
print(f"  buffer:           {buffer}px on each side (total of {buffer*2}px added to both width and height)")
print(f"  WRIST RIB KNIT drawn in red from ({start_x}, {start_y}) to ({end_x}, {end_y})")
print(f"    → Size: {knit_rect_width} px wide × {knit_rect_height} px tall")
print(f"    → Bottom row color pattern: red, green, yellow, blue (repeating)")
