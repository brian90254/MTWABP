# BRIAN COX copyright 2025
# HOW TO USE:
# python src/ParametricPattern_ConvertPrintable_8.py images/YourInputFile.bmp

import cv2
import numpy as np
import os
import sys

# === COMMAND-LINE ARGUMENTS ===
if len(sys.argv) < 2:
    print("Usage: python src/ParametricPattern_ConvertPrintable_8.py <input_bmp_file>")
    sys.exit(1)

input_path = sys.argv[1]
if not input_path.lower().endswith('.bmp'):
    print("Error: Input file must be a .bmp file")
    sys.exit(1)

# Automatically generate output path by changing extension to .png
output_path = os.path.splitext(input_path)[0] + '.png'

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
