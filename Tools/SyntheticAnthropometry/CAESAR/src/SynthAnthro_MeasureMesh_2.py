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

# Configuration
obj_filename = "OBJ/SPRING_MALE/SPRING0001.obj"
measurement_filename = "measurements.txt"

def load_vertices_from_obj(filename):
    vertices = []
    with open(filename, 'r') as file:
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
            name = parts[0]
            indices = [int(p) for p in parts[1:]]
            measurements[name] = indices
    return measurements

def calculate_chain_distance(vertices, indices):
    total_distance = 0.0
    for i in range(len(indices) - 1):
        a_idx = indices[i]
        b_idx = indices[i + 1]

        # Adjust for OBJ's 1-based indexing if necessary
        va = vertices[a_idx]
        vb = vertices[b_idx]

        dist = math.sqrt(sum((va[j] - vb[j]) ** 2 for j in range(3)))
        total_distance += dist
    return total_distance

def main():
    vertices = load_vertices_from_obj(obj_filename)
    measurements = load_measurements(measurement_filename)

    for name, indices in measurements.items():
        if max(indices) >= len(vertices):
            print(f"Warning: Index out of range in {name}")
            continue
        distance = calculate_chain_distance(vertices, indices)
        print(f"{name}: {distance:.6f} units")

if __name__ == "__main__":
    main()
