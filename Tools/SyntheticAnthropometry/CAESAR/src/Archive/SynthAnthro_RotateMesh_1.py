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
ANGLE_DEG = 45
ANGLE_RAD = math.radians(ANGLE_DEG)

# Rotation around Y-axis
def rotate_vertex_y(x, y, z):
    x_new = x * math.cos(ANGLE_RAD) + z * math.sin(ANGLE_RAD)
    y_new = y
    z_new = -x * math.sin(ANGLE_RAD) + z * math.cos(ANGLE_RAD)
    return x_new, y_new, z_new

def process_obj_file(filepath):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    rotated_lines = []
    for line in lines:
        if line.startswith("v "):
            parts = line.strip().split()
            x, y, z = map(float, parts[1:])
            x, y, z = rotate_vertex_y(x, y, z)
            rotated_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        elif line.startswith("vn "):
            parts = line.strip().split()
            x, y, z = map(float, parts[1:])
            x, y, z = rotate_vertex_y(x, y, z)
            # Re-normalize vector
            length = math.sqrt(x*x + y*y + z*z)
            if length > 0:
                x /= length
                y /= length
                z /= length
            rotated_lines.append(f"vn {x:.6f} {y:.6f} {z:.6f}\n")
        else:
            rotated_lines.append(line)

    with open(filepath, 'w') as file:
        file.writelines(rotated_lines)
    print(f"Rotated: {os.path.basename(filepath)}")

# Main
if __name__ == "__main__":
    for filename in os.listdir(SOURCE_DIR):
        if filename.lower().endswith(".obj"):
            filepath = os.path.join(SOURCE_DIR, filename)
            process_obj_file(filepath)
