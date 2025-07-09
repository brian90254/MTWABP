import cv2
import numpy as np

# === CONFIGURATION ===
input_path = 'images/ParametricPattern_KnitGlove_20250602_230407.bmp'
output_path = 'images/Printable_KnitGlove_20250602_230407.png'
scale_factor = 100
border_color = (0, 0, 0)  # black

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
        color = image[y, x].tolist()
        top_left_x = x * scale_factor
        top_left_y = y * scale_factor
        bottom_right_x = top_left_x + scale_factor - 1
        bottom_right_y = top_left_y + scale_factor - 1

        # Fill the entire block with the pixel color
        cv2.rectangle(
            scaled_image,
            (top_left_x, top_left_y),
            (bottom_right_x, bottom_right_y),
            color,
            thickness=-1
        )

        # Draw the border
        cv2.rectangle(
            scaled_image,
            (top_left_x, top_left_y),
            (bottom_right_x, bottom_right_y),
            border_color,
            thickness=1
        )

# === SAVE AS PNG ===
cv2.imwrite(output_path, scaled_image)
print(f"Saved scaled image to {output_path}")
