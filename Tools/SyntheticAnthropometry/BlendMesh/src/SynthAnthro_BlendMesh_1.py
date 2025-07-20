# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SyntheticAnthropometry/BlendMesh
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/SynthAnthro_BlendMesh_1.py

# import cv2
# import numpy as np
# from datetime import datetime
# import os
# import math
# import sys
# import math
# import csv
# import pandas as pd
# import numpy as np
# import random

import re

def load_obj(filepath):
    vertices = []
    normals = []
    faces = []
    with open(filepath, 'r') as file:
        for line in file:
            if line.startswith('v '):  # Vertex
                parts = line.strip().split()
                vertices.append(tuple(float(x) for x in parts[1:4]))
            elif line.startswith('vn '):  # Vertex normal
                parts = line.strip().split()
                normals.append(tuple(float(x) for x in parts[1:4]))
            elif line.startswith('f '):  # Face
                faces.append(line.strip())
    return vertices, normals, faces

def average_triplets(list1, list2):
    return [tuple((a + b) / 2 for a, b in zip(v1, v2)) for v1, v2 in zip(list1, list2)]

def write_obj(filepath, vertices, normals, faces):
    with open(filepath, 'w') as file:
        for v in vertices:
            file.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for vn in normals:
            file.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")
        for f in faces:
            file.write(f + "\n")

def main():
    file1 = "OBJ/TEST/SPRING0001.obj"
    file2 = "OBJ/TEST/SPRING0002.obj"
    output_file = "SPRING_blended.obj"

    verts1, norms1, faces1 = load_obj(file1)
    verts2, norms2, faces2 = load_obj(file2)

    if len(verts1) != len(verts2):
        raise ValueError("Mismatch in vertex count.")
    if len(norms1) != len(norms2):
        raise ValueError("Mismatch in normal count.")
    if faces1 != faces2:
        raise ValueError("Face definitions do not match.")

    blended_verts = average_triplets(verts1, verts2)
    blended_norms = average_triplets(norms1, norms2)

    write_obj(output_file, blended_verts, blended_norms, faces1)
    print(f"Blended OBJ written to: {output_file}")

if __name__ == "__main__":
    main()
