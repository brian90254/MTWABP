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
#   python src/SynthAnthro_BlendMesh_4.py

import os
import sys
import csv
import numpy as np
from collections import defaultdict

# Constants for input directories
CSV_DIR = "CSV"
#OBJ_DIR = "OBJ/SPRING_MALE"
#OUTPUT_DIR = "OBJ/BLENDED_MALE"
#CSV_FILENAME = "SynthAnthro_AggregateExtremes_MALE_1.csv"  # You can rename this as needed

def prompt_for_obj_input_directory():
    base_dir = "OBJ"
    subdirs = [
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d)) and d.startswith("SPRING_")
    ]

    subdirs.sort()  # <-- Sort alphabetically
    
    if not subdirs:
        print(f"No 'SPRING_' subdirectories found in {base_dir}")
        sys.exit(1)

    print(f"\nAvailable OBJ subdirectories in '{base_dir}' that start with 'SPRING_':")
    for i, d in enumerate(subdirs):
        print(f"[{i}] {d}")
    
    while True:
        try:
            index = int(input("\nEnter the number of the OBJ subdirectory to process: ").strip())
            if 0 <= index < len(subdirs):
                return os.path.join(base_dir, subdirs[index])
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def prompt_for_obj_output_directory():
    base_dir = "OBJ"
    subdirs = [
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d)) and d.startswith("BLENDED_")
    ]

    subdirs.sort()  # <-- Sort alphabetically

    if not subdirs:
        print(f"No 'BLENDED_' subdirectories found in {base_dir}")
        sys.exit(1)

    print(f"\nAvailable OBJ subdirectories in '{base_dir}' that start with 'BLENDED_':")
    for i, d in enumerate(subdirs):
        print(f"[{i}] {d}")
    
    while True:
        try:
            index = int(input("\nEnter the number of the OBJ subdirectory to process: ").strip())
            if 0 <= index < len(subdirs):
                return os.path.join(base_dir, subdirs[index])
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def prompt_for_measurement_file():
    base_dir = "CSV"
    files = [
        f for f in os.listdir(base_dir)
        if f.startswith("SynthAnthro_AggregateExtremes") and f.lower().endswith('.csv')
    ]

    files.sort()  # <-- Sort alphabetically

    if not files:
        print(f"No CSV files starting with 'SynthAnthro_AggregateExtremes' found in {base_dir}")
        sys.exit(1)

    print(f"\nAvailable CSV files in '{base_dir}' starting with 'SynthAnthro_AggregateExtremes':")
    for i, f in enumerate(files):
        print(f"[{i}] {f}")
    
    while True:
        try:
            index = int(input("\nEnter the number of the measurement CSV file to use: ").strip())
            if 0 <= index < len(files):
                return os.path.join(base_dir, files[index])
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

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

def average_group(file_list):
    assert file_list, "Empty file list."

    # Load first file to initialize
    base_path = os.path.join(OBJ_DIR, file_list[0])
    base_vertices, base_normals, base_faces = load_obj(base_path)
    vert_accum = np.copy(base_vertices)
    norm_accum = np.copy(base_normals)

    for fname in file_list[1:]:
        path = os.path.join(OBJ_DIR, fname)
        v, n, faces = load_obj(path)
        if len(v) != len(vert_accum) or len(n) != len(norm_accum):
            raise ValueError(f"Mismatch in {fname}")
        vert_accum += v
        norm_accum += n

    vert_avg = vert_accum / len(file_list)
    norm_avg = norm_accum / len(file_list)

    return vert_avg, norm_avg, base_faces

def write_obj(filepath, vertices, normals, faces):
    with open(filepath, 'w') as file:
        for v in vertices:
            file.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for n in normals:
            file.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
        for f in faces:
            file.write(f + "\n")

def main():
    #csv_path = os.path.join(CSV_DIR, CSV_FILENAME)
    csv_path = CSV_FILENAME
    with open(csv_path, 'r', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        columns = defaultdict(list)

        for row in reader:
            for col_idx, filename in enumerate(row):
                if filename.strip():
                    columns[headers[col_idx]].append(filename.strip())

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for group_name, file_list in columns.items():
        print(f"Processing group: {group_name} with {len(file_list)} files")
        verts, norms, faces = average_group(file_list)
        out_path = os.path.join(OUTPUT_DIR, f"{group_name}_blended.obj")
        write_obj(out_path, verts, norms, faces)
        print(f"→ Saved to {out_path}")

if __name__ == "__main__":
    # -- Get the OBJ directory with the indexex meshes
    print("\nPlease choose SPRING_MALE or SPRING_FEMALE as the INPUT directory")
    OBJ_DIR = prompt_for_obj_input_directory()
    # -- Get the CSV file with the OBJ file names
    print("\nPlease choose a CSV file of IDs to aggregate")
    CSV_FILENAME = prompt_for_measurement_file()
    # -- Get the OBJ directory to output blended meshes to
    print("\nPlease choose BLENDED_MALE or BLENDED_FEMALE as the OUTPUT directory")
    OUTPUT_DIR = prompt_for_obj_output_directory()
    # -- MAIN --
    main()
