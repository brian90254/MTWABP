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
#   python src/SynthAnthro_MeasureMesh_8_MALE.py
# ...or
#   python src/SynthAnthro_MeasureMesh_8_FEMALE.py

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
obj_directory = "OBJ/SPRING_MALE"
#measurement_filename = "measurements2.txt"
measurement_filename = "CSV/SynthAnthro_CAESAR_POMs_2.csv"
output_csv = "MEASUREMENTS/measurementResults_SPRING_MALE.csv"

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

def calculate_chain_distance(vertices, indices):
    if len(indices) == 4:
        va1 = np.array(vertices[indices[0]])
        va2 = np.array(vertices[indices[1]])
        midpoint_a = (va1 + va2) / 2

        vb1 = np.array(vertices[indices[2]])
        vb2 = np.array(vertices[indices[3]])
        midpoint_b = (vb1 + vb2) / 2

        dist = np.linalg.norm(midpoint_a - midpoint_b)
        return dist
    else:
        total_distance = 0.0
        for i in range(len(indices) - 1):
            a_idx = indices[i]
            b_idx = indices[i + 1]
            if max(a_idx, b_idx) >= len(vertices):
                continue
            va = np.array(vertices[a_idx])
            vb = np.array(vertices[b_idx])
            dist = np.linalg.norm(va - vb)
            total_distance += dist
        return total_distance

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

    color_map = {}
    np.random.seed(42)
    for name in measurements:
        color_map[name] = tuple(np.random.randint(50, 255, size=3).tolist())

    for name, indices in measurements.items():
        points = []
        for idx in indices:
            if idx >= len(vertices):
                continue
            p = vertices[idx]
            x = int((p[ax1] - min_x) * scale_factor + 50)
            y = int((p[ax2] - min_y) * scale_factor + 50)
            points.append((x, y))

        if len(indices) == 4 and len(points) == 4:
            midpoint_a = (
                (points[0][0] + points[1][0]) // 2,
                (points[0][1] + points[1][1]) // 2
            )
            midpoint_b = (
                (points[2][0] + points[3][0]) // 2,
                (points[2][1] + points[3][1]) // 2
            )
            cv2.line(img, midpoint_a, midpoint_b, color_map[name], 2)
        elif len(points) >= 2:
            for i in range(len(points) - 1):
                cv2.line(img, points[i], points[i + 1], color_map[name], 2)

    cv2.imshow(window_name, img)
    key = cv2.waitKey(0)
    cv2.destroyAllWindows()

def process_files_with_combined_overlay_and_csv():
    measurements = load_measurements(measurement_filename)
    measurement_names = list(measurements.keys())

    results = []

    for filename in sorted(os.listdir(obj_directory)):
        if filename.lower().endswith(".obj"):
            filepath = os.path.join(obj_directory, filename)
            print(f"Processing {filename}...")

            vertices = load_vertices_from_obj(filepath)

            result_row = {"File": filename}
            for name in measurement_names:
                indices = measurements[name]
                distance = calculate_chain_distance(vertices, indices)
                result_row[name] = distance
            results.append(result_row)

            #show_combined_measurements(vertices, measurements)
            #show_combined_measurements(vertices, measurements, projection_axis="xy", window_name="Combined Measurement X-Y")
            #show_combined_measurements(vertices, measurements, projection_axis="xz")
            #show_combined_measurements(vertices, measurements, projection_axis="yz", window_name="Combined Measurement Y-Z")

    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"Saved results to {output_csv}")
    print(df.head())

if __name__ == "__main__":
    process_files_with_combined_overlay_and_csv()
