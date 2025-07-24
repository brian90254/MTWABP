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

# import re

# def load_obj(filepath):
#     vertices = []
#     normals = []
#     faces = []
#     with open(filepath, 'r') as file:
#         for line in file:
#             if line.startswith('v '):  # Vertex
#                 parts = line.strip().split()
#                 vertices.append(tuple(float(x) for x in parts[1:4]))
#             elif line.startswith('vn '):  # Vertex normal
#                 parts = line.strip().split()
#                 normals.append(tuple(float(x) for x in parts[1:4]))
#             elif line.startswith('f '):  # Face
#                 faces.append(line.strip())
#     return vertices, normals, faces

# def average_triplets(list1, list2):
#     return [tuple((a + b) / 2 for a, b in zip(v1, v2)) for v1, v2 in zip(list1, list2)]

# def write_obj(filepath, vertices, normals, faces):
#     with open(filepath, 'w') as file:
#         for v in vertices:
#             file.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
#         for vn in normals:
#             file.write(f"vn {vn[0]:.6f} {vn[1]:.6f} {vn[2]:.6f}\n")
#         for f in faces:
#             file.write(f + "\n")

# def main():
#     file1 = "OBJ/TEST/SPRING0001.obj"
#     file2 = "OBJ/TEST/SPRING0002.obj"
#     output_file = "SPRING_blended.obj"

#     verts1, norms1, faces1 = load_obj(file1)
#     verts2, norms2, faces2 = load_obj(file2)

#     if len(verts1) != len(verts2):
#         raise ValueError("Mismatch in vertex count.")
#     if len(norms1) != len(norms2):
#         raise ValueError("Mismatch in normal count.")
#     if faces1 != faces2:
#         raise ValueError("Face definitions do not match.")

#     blended_verts = average_triplets(verts1, verts2)
#     blended_norms = average_triplets(norms1, norms2)

#     write_obj(output_file, blended_verts, blended_norms, faces1)
#     print(f"Blended OBJ written to: {output_file}")

# if __name__ == "__main__":
#     main()

# import os
# import csv
# import numpy as np
# from collections import defaultdict

# # Constants for input directories
# CSV_DIR = "CSV"
# OBJ_DIR = "OBJ/SPRING_MALE"
# OUTPUT_DIR = "OBJ/BLENDED_MALE"
# CSV_FILENAME = "SynthAnthro_AggregateExtremes_MALE_1.csv"  # You can rename this as needed

# def load_obj(filepath):
#     vertices, normals, faces = [], [], []
#     with open(filepath, 'r') as file:
#         for line in file:
#             if line.startswith('v '):
#                 parts = list(map(float, line.strip().split()[1:4]))
#                 vertices.append(parts)
#             elif line.startswith('vn '):
#                 parts = list(map(float, line.strip().split()[1:4]))
#                 normals.append(parts)
#             elif line.startswith('f '):
#                 faces.append(line.strip())
#     return np.array(vertices), np.array(normals), faces

# def average_group(file_list):
#     assert file_list, "Empty file list."

#     # Load first file to initialize
#     base_path = os.path.join(OBJ_DIR, file_list[0])
#     base_vertices, base_normals, base_faces = load_obj(base_path)
#     vert_accum = np.copy(base_vertices)
#     norm_accum = np.copy(base_normals)

#     for fname in file_list[1:]:
#         path = os.path.join(OBJ_DIR, fname)
#         v, n, faces = load_obj(path)
#         if len(v) != len(vert_accum) or len(n) != len(norm_accum):
#             raise ValueError(f"Mismatch in {fname}")
#         vert_accum += v
#         norm_accum += n

#     vert_avg = vert_accum / len(file_list)
#     norm_avg = norm_accum / len(file_list)

#     return vert_avg, norm_avg, base_faces

# def write_obj(filepath, vertices, normals, faces):
#     with open(filepath, 'w') as file:
#         for v in vertices:
#             file.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
#         for n in normals:
#             file.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
#         for f in faces:
#             file.write(f + "\n")

# def main():
#     csv_path = os.path.join(CSV_DIR, CSV_FILENAME)

#     with open(csv_path, 'r', newline='') as f:
#         reader = csv.reader(f)
#         headers = next(reader)
#         columns = defaultdict(list)

#         for row in reader:
#             for col_idx, filename in enumerate(row):
#                 if filename.strip():
#                     columns[headers[col_idx]].append(filename.strip())

#     os.makedirs(OUTPUT_DIR, exist_ok=True)

#     for group_name, file_list in columns.items():
#         print(f"Processing group: {group_name} with {len(file_list)} files")
#         verts, norms, faces = average_group(file_list)
#         out_path = os.path.join(OUTPUT_DIR, f"{group_name}_blended.obj")
#         write_obj(out_path, verts, norms, faces)
#         print(f"→ Saved to {out_path}")

# if __name__ == "__main__":
#     main()

import os
import csv
import numpy as np

# Directories
#INPUT_DIR = "blended_output"
INPUT_DIR = "OBJ/BLENDED_MALE"
CSV_FILE = "CSV/SynthAnthro_Target_Test2_MALE.csv"
OUTPUT_FILE = "OBJ/DECODED/SynthAnthro_Target_Test1_MALE.obj"

def load_obj(filepath):
    vertices, normals, faces = [], [], []
    with open(filepath, 'r') as file:
        for line in file:
            if line.startswith('v '):
                parts = list(map(float, line.strip().split()[1:4]))
                vertices.append(parts)
            elif line.startswith('vn '):
                parts = list(map(float, line.strip().split()[1:4]))
                normals.append(parts)
            elif line.startswith('f '):
                faces.append(line.strip())
    return np.array(vertices), np.array(normals), faces

def write_obj(filepath, vertices, normals, faces):
    with open(filepath, 'w') as file:
        for v in vertices:
            file.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for n in normals:
            file.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
        for f in faces:
            file.write(f + "\n")

def weighted_average(files_and_weights):
    weighted_vertices = None
    weighted_normals = None
    faces = None

    for idx, (filename, weight) in enumerate(files_and_weights):
        path = os.path.join(INPUT_DIR, filename)
        vertices, normals, file_faces = load_obj(path)

        if weighted_vertices is None:
            weighted_vertices = np.zeros_like(vertices)
            weighted_normals = np.zeros_like(normals)
            faces = file_faces  # Assume all face structures are identical

        if vertices.shape != weighted_vertices.shape or normals.shape != weighted_normals.shape:
            raise ValueError(f"Shape mismatch in file: {filename}")

        weighted_vertices += weight * vertices
        weighted_normals += weight * normals

    return weighted_vertices, weighted_normals, faces

def main():
    files_and_weights = []

    # Load weights from CSV
    with open(CSV_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['File'].strip()
            weight = float(row['Weight'])
            files_and_weights.append((filename, weight))

    print(f"Blending {len(files_and_weights)} files using weighted average...")
    v_avg, n_avg, faces = weighted_average(files_and_weights)

    write_obj(OUTPUT_FILE, v_avg, n_avg, faces)
    print(f"→ Weighted blend saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
