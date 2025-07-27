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
#   python src/SynthAnthro_MeasureMesh_10.py
# COMMAND LINE WILL FIRST PROMPT FOR AN "OBJ" SOURCE DIRECTORY
#   [1] == TEST
# COMMAND LINE WITH SECOND PROMPT YOU FOR A MEASUREMENT LIST FILE IN THE "CSV" DIRECORY
#   [1] == SynthAnthro_CAESAR_POMs_2.csv
#
# ...or
# RUN THE "command" SCRIPT DIRECTLY, DOUBLE CLICK:
#   runSynthAnthro_MeasureMesh.command

import os
import math

# Constants
SOURCE_DIR = "OBJ/BLENDED_FEMALE"
OUTPUT_DIR = "OBJ/BLENDED_FEMALE_ROTATE_SCALE"
ANGLE_DEG = 52
ANGLE_RAD = math.radians(ANGLE_DEG)
SCALE_FACTOR = 100.0

def rotate_vertex_x(x, y, z, angle_rad):
    x_new = x
    y_new = y * math.cos(angle_rad) - z * math.sin(angle_rad)
    z_new = y * math.sin(angle_rad) + z * math.cos(angle_rad)
    return x_new, y_new, z_new

def rotate_vertex_y(x, y, z, angle_rad):
    x_new = x * math.cos(angle_rad) + z * math.sin(angle_rad)
    y_new = y
    z_new = -x * math.sin(angle_rad) + z * math.cos(angle_rad)
    return x_new, y_new, z_new

def rotate_vertex_z(x, y, z, angle_rad):
    x_new = x * math.cos(angle_rad) - y * math.sin(angle_rad)
    y_new = x * math.sin(angle_rad) + y * math.cos(angle_rad)
    z_new = z
    return x_new, y_new, z_new

def scale_vertex(x, y, z, scale):
    return x * scale, y * scale, z * scale

def process_obj_file(filepath, outpath):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    transformed_lines = []
    for line in lines:
        if line.startswith("v "):
            parts = line.strip().split()
            x, y, z = map(float, parts[1:])
            x, y, z = rotate_vertex_z(x, y, z, ANGLE_RAD)
            x, y, z = scale_vertex(x, y, z, SCALE_FACTOR)
            transformed_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        elif line.startswith("vn "):
            parts = line.strip().split()
            x, y, z = map(float, parts[1:])
            x, y, z = rotate_vertex_z(x, y, z, ANGLE_RAD)
            length = math.sqrt(x*x + y*y + z*z)
            if length > 0:
                x /= length
                y /= length
                z /= length
            transformed_lines.append(f"vn {x:.6f} {y:.6f} {z:.6f}\n")
        else:
            transformed_lines.append(line)

    with open(outpath, 'w') as file:
        file.writelines(transformed_lines)
    print(f"Saved: {os.path.basename(outpath)}")

# Main
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in os.listdir(SOURCE_DIR):
        if filename.lower().endswith(".obj"):
            src_path = os.path.join(SOURCE_DIR, filename)
            dst_path = os.path.join(OUTPUT_DIR, filename)
            process_obj_file(src_path, dst_path)
