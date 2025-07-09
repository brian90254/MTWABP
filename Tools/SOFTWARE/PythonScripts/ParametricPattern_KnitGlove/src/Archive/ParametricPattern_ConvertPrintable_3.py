import cv2
import numpy as np

# === CONFIGURATION ===
input_path = 'images/ParametricPattern_KnitGlove_20250602_230407.bmp'
output_path = 'images/Printable_KnitGlove_20250602_230407_3.png'
scale_factor = 100
border_color = (0, 0, 0)  # black
text_color = (0, 0, 0)    # black
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 2
font_thickness = 3

target_color = (255, 255, 0)  # cyan (BGR format in OpenCV)
text = "6"

# === COLOR TO TEXT MAPPING ===
color_text_map = {
    (0, 255, 255): "6",     # yellowish cyan
    (255, 0, 255): "4",     # magenta
    (255, 255, 255): "7",   # white
    (0, 0, 255): "5",       # red (note: BGR in OpenCV)
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
        #color = tuple(image[y, x])  # BGR format
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

        # If color matches mapping, draw corresponding number
        #if color in color_text_map:
        if color == list(target_color):
            #text = color_text_map[color]
            text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
            text_width, text_height = text_size
            text_x = top_left_x + (scale_factor - text_width) // 2
            text_y = top_left_y + (scale_factor + text_height) // 2
            cv2.putText(
                scaled_image,
                text,
                (text_x, text_y),
                font,
                font_scale,
                text_color,
                font_thickness,
                lineType=cv2.LINE_AA
            )

# === SAVE AS PNG ===
cv2.imwrite(output_path, scaled_image)
print(f"Saved scaled image to {output_path}")
