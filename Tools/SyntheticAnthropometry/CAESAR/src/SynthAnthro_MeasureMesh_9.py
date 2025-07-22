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
# BRIAN COX copyright 2025

import cv2
import numpy as np
import os
import math
import sys
import csv
import pandas as pd

def prompt_for_obj_directory():
    base_dir = "OBJ"
    print(f"\nAvailable OBJ subdirectories in '{base_dir}':")
    subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    for d in subdirs:
        print(f"  - {d}")
    selected = input("\nEnter the name of the OBJ subdirectory to process: ").strip()
    selected_path = os.path.join(base_dir, selected)
    if not os.path.isdir(selected_path):
        print(f"Error: '{selected_path}' is not a valid directory.")
        sys.exit(1)
    return selected_path

def prompt_for_measurement_file():
    base_dir = "CSV"
    print(f"\nAvailable CSV files in '{base_dir}':")
    files = [f for f in os.listdir(base_dir) if f.lower().endswith('.csv')]
    for f in files:
        print(f"  - {f}")
    selected = input("\nEnter the name of the measurement CSV file to use: ").strip()
    selected_path = os.path.join(base_dir, selected)
    if not os.path.isfile(selected_path):
        print(f"Error: '{selected_path}' is not a valid file.")
        sys.exit(1)
    return selected_path

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

def process_files_with_combined_overlay_and_csv(obj_directory, measurement_filename):
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

    os.makedirs("MEASUREMENTS", exist_ok=True)
    dir_label = os.path.basename(obj_directory)
    output_csv = f"MEASUREMENTS/measurementResults_{dir_label}.csv"

    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Saved results to: {output_csv}")
    print(df.head())

if __name__ == "__main__":
    obj_directory = prompt_for_obj_directory()
    measurement_filename = prompt_for_measurement_file()
    process_files_with_combined_overlay_and_csv(obj_directory, measurement_filename)
