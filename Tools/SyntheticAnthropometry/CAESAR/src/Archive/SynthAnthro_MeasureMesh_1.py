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

# Configuration
obj_filename = "OBJ/SPRING_MALE/SPRING0001.obj"
# index_a = 365
# index_b = 723
index_a = 369
index_b = 358

# Function to read vertices from OBJ file
def load_vertices_from_obj(filename):
    vertices = []
    with open(filename, 'r') as file:
        for line in file:
            if line.startswith('v '):
                parts = line.strip().split()
                # Parse x, y, z as floats
                vertex = tuple(map(float, parts[1:4]))
                vertices.append(vertex)
    return vertices

# Load vertices
vertices = load_vertices_from_obj(obj_filename)

# Check index bounds
if max(index_a, index_b) >= len(vertices):
    raise ValueError("Vertex index out of range. OBJ file has only {} vertices.".format(len(vertices)))

# Get coordinates of the two vertices
va = vertices[index_a]
vb = vertices[index_b]

# Calculate Euclidean distance
distance = math.sqrt(sum((va[i] - vb[i]) ** 2 for i in range(3)))

print(f"Distance between vertex {index_a} and vertex {index_b}: {distance:.6f} units")
