# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SyntheticAnthropometry/CAESAR
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/SynthAnthro_MeasureMesh_1.py

import cv2
import numpy as np
from datetime import datetime
import os
import math
import sys
import math
import csv
import pandas as pd
import numpy as np
import random

# Configuration
obj_directory = "OBJ/TEST"
measurement_filename = "measurements2.txt"

def load_vertices_from_obj(filepath):
    vertices = []
    with open(filepath, 'r') as file:
        for line in file:
            if line.startswith('v '):
                parts = line.strip().split()
                vertex = tuple(map(float, parts[1:4]))
                vertices.append(vertex)
    return vertices

def load_measurements(filename):
    measurements = {}
    with open(filename, 'r') as file:
        for line in file:
            if not line.strip():
                continue
            parts = line.strip().split(',')
            name = parts[0].strip()
            indices = [int(p) for p in parts[1:] if p.strip().isdigit()]
            if indices:
                measurements[name] = indices
    return measurements

def show_combined_measurements(vertices, measurements, projection_axis="xy", window_name="Combined Measurement Overlay"):
    axis_map = {
        "xy": (0, 1),
        "xz": (0, 2),
        "yz": (1, 2)
    }
    ax1, ax2 = axis_map.get(projection_axis, (0, 1))

    coords = np.array(vertices)
    min_x, max_x = coords[:, ax1].min(), coords[:, ax1].max()
    min_y, max_y = coords[:, ax2].min(), coords[:, ax2].max()

    scale_factor = 800 / max(max_x - min_x, max_y - min_y)
    img_size = (1000, 1000, 3)

    img = np.ones(img_size, dtype=np.uint8) * 255

    # Assign random colors for each measurement name
    rng = random.Random(42)
    color_map = {name: (rng.randint(50, 255), rng.randint(50, 255), rng.randint(50, 255)) for name in measurements}

    for name, indices in measurements.items():
        points = []
        for idx in indices:
            if idx >= len(vertices):
                continue
            p = vertices[idx]
            x = int((p[ax1] - min_x) * scale_factor + 50)
            y = int((p[ax2] - min_y) * scale_factor + 50)
            points.append((x, y))

        if len(points) >= 2:
            for i in range(len(points) - 1):
                cv2.line(img, points[i], points[i + 1], color_map[name], 2)

    cv2.imshow(window_name, img)
    key = cv2.waitKey(0)  # Wait for key press before showing next file
    cv2.destroyAllWindows()

def process_files_with_combined_overlay():
    measurements = load_measurements(measurement_filename)

    for filename in sorted(os.listdir(obj_directory)):
        if filename.lower().endswith(".obj"):
            filepath = os.path.join(obj_directory, filename)
            print(f"Visualizing {filename}...")

            vertices = load_vertices_from_obj(filepath)

            #show_combined_measurements(vertices, measurements, projection_axis="xy")
            #show_combined_measurements(vertices, measurements, projection_axis="xz")
            show_combined_measurements(vertices, measurements, projection_axis="yz")

if __name__ == "__main__":
    process_files_with_combined_overlay()
