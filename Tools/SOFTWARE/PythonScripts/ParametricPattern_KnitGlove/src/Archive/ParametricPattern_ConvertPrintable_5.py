import cv2
import numpy as np

# === CONFIGURATION ===
input_path = 'images/ParametricPattern_KnitGlove_20250603_114242.bmp'
output_path = 'images/Printable_KnitGlove_20250602_230407_5.png'
scale_factor = 100
border_color = (0, 0, 0)  # black border
text_color = (0, 0, 0)    # black text
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 2
font_thickness = 3

# === COLOR TO TEXT MAPPING (BGR format for OpenCV) ===
color_text_map = {
    (255, 255, 0): "6",     # (0, 255, 255) in RGB — cyan
    (255, 0, 255): "4",     # (255, 0, 255) in RGB — magenta
    (255, 255, 255): "7",   # white
    (255, 0, 0): "5",       # (0, 0, 255) in RGB — red
    (192, 192, 0): "106",  # (0, 192, 192) in RGB — cyan with yellowish tint
    (160, 160, 160): "107",  # (192, 192, 192) in RGB — light gray
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
        color = tuple(int(c) for c in image[y, x])  # Convert BGR array to int tuple
        top_left_x = x * scale_factor
        top_left_y = y * scale_factor
        bottom_right_x = top_left_x + scale_factor - 1
        bottom_right_y = top_left_y + scale_factor - 1

        # Fill the block with the pixel color
        cv2.rectangle(
            scaled_image,
            (top_left_x, top_left_y),
            (bottom_right_x, bottom_right_y),
            color,
            -1  # thickness=-1 means filled
        )

        # Draw the 1px black border
        cv2.rectangle(
            scaled_image,
            (top_left_x, top_left_y),
            (bottom_right_x, bottom_right_y),
            border_color,
            1
        )

        # If pixel color matches, draw number in center
        if color in color_text_map:
            text = color_text_map[color]
            # CHECK TO SEE IN TEXT SIZE SHOULD BE SMALL
            if text == "106":
                font_scale = 1.5
            elif text == "107":
                font_scale = 1.5
            else:
                font_scale = 2
            text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
            text_width, text_height = text_size
            text_x = top_left_x + (scale_factor - text_width) // 2
            text_y = top_left_y + (scale_factor + text_height) // 2
            # CHECK TO SEE IF TEXT COLOR SHOULD BE WHITE
            if text == "5":
                text_color = (255, 255, 255)  # yellowish cyan for "6"
            else:
                text_color = (0, 0, 0)
            # # CHECK TO SEE IN TEXT SIZE SHOULD BE SMALL
            # if text == "106":
            #     font_scale = 1
            # elif text == "107":
            #     font_scale = 1
            # else:
            #     font_scale = 2
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

# === SAVE THE OUTPUT IMAGE ===
cv2.imwrite(output_path, scaled_image)
print(f"Saved scaled image to {output_path}")
