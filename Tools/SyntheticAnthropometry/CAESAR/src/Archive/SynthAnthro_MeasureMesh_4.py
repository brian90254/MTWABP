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

# Configuration
obj_directory = "OBJ/TEST"
measurement_filename = "measurements2.txt"
output_csv = "measurement_results.csv"

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
            indices = []
            for p in parts[1:]:
                p = p.strip()
                if p.isdigit():
                    indices.append(int(p))
            if indices:
                measurements[name] = indices
    return measurements

def calculate_chain_distance(vertices, indices):
    total_distance = 0.0
    for i in range(len(indices) - 1):
        a_idx = indices[i]
        b_idx = indices[i + 1]
        if max(a_idx, b_idx) >= len(vertices):
            continue
        va = vertices[a_idx]
        vb = vertices[b_idx]
        dist = math.sqrt(sum((va[j] - vb[j]) ** 2 for j in range(3)))
        total_distance += dist
    return total_distance

def process_all_files():
    measurements = load_measurements(measurement_filename)
    result_rows = []

    for filename in os.listdir(obj_directory):
        if filename.lower().endswith(".obj"):
            filepath = os.path.join(obj_directory, filename)
            print(f"Processing {filename}...")

            vertices = load_vertices_from_obj(filepath)

            for name, indices in measurements.items():
                distance = calculate_chain_distance(vertices, indices)
                result_rows.append([filename, name, f"{distance:.6f}"])

    return result_rows

def write_results_to_csv(rows, output_path):
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File", "Measurement", "Distance"])
        writer.writerows(rows)
    print(f"Results saved to {output_path}")

def main():
    rows = process_all_files()
    write_results_to_csv(rows, output_csv)

if __name__ == "__main__":
    main()
