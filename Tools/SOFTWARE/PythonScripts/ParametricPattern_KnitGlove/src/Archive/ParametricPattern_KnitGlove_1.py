import cv2
import numpy as np
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Create a red bitmap image with given dimensions.")
parser.add_argument("width", type=int, help="Width of the image in pixels")
parser.add_argument("height", type=int, help="Height of the image in pixels")
args = parser.parse_args()

# Create an image of specified dimensions filled with red (BGR: 0, 0, 255)
image = np.zeros((args.height, args.width, 3), dtype=np.uint8)
image[:] = (0, 0, 255)  # Red in OpenCV uses BGR format

# Save the image
cv2.imwrite("red_image.bmp", image)
print(f"Saved red_image.bmp with size {args.width}x{args.height}")
