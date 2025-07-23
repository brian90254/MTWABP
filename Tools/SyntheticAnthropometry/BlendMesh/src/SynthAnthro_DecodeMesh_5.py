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
#   python src/SynthAnthro_BlendMesh_5.py


import os
import csv
import numpy as np

# Directories
#INPUT_DIR = "blended_output"
# INPUT_DIR = "OBJ/BLENDED_MALE"
# CSV_FILE = "CSV/SynthAnthro_Target_Test3_MALE.csv"
# OUTPUT_FILE = "OBJ/DECODED/SynthAnthro_Target_Test3_MALE.obj"

def prompt_for_obj_input_directory():
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

def prompt_for_target_file():
    base_dir = "CSV"
    files = [
        f for f in os.listdir(base_dir)
        if f.startswith("SynthAnthro_Target") and f.lower().endswith('.csv')
    ]

    files.sort()  # <-- Sort alphabetically

    if not files:
        print(f"No CSV files starting with 'SynthAnthro_Target' found in {base_dir}")
        sys.exit(1)

    print(f"\nAvailable CSV files in '{base_dir}' starting with 'SynthAnthro_Target':")
    for i, f in enumerate(files):
        print(f"[{i}] {f}")
    
    while True:
        try:
            index = int(input("\nEnter the number of the target CSV file to use: ").strip())
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

    # Generate output filename from target file
    output_basename = os.path.basename(CSV_FILE)  # e.g., "SynthAnthro_Target_Test3_MALE.obj"
    #output_filename = "output_" + output_basename
    output_filename = output_basename
    #output_path = os.path.join("OBJ", "DECODED", output_filename)
    OUTPUT_FILE = os.path.join("OBJ", "DECODED", output_filename)

    write_obj(OUTPUT_FILE, v_avg, n_avg, faces)
    print(f"→ Weighted blend saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    # -- Get the OBJ directory with the indexex meshes
    print("\nPlease choose SPRING_MALE or SPRING_FEMALE as the INPUT directory")
    INPUT_DIR = prompt_for_obj_input_directory()
    # -- Get the CSV file with the OBJ file names
    print("\nPlease choose a CSV file of IDs to aggregate")
    CSV_FILE = prompt_for_target_file()
    # -- MAIN --
    main()
