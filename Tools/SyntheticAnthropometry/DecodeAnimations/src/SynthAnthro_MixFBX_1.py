# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SyntheticAnthropometry/DecodeAnimations/
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/SynthAnthro_MixFBX_1.py FBX/FEMALE_SHAPE_3_HIGH_RumbaDancing_1.fbx MALE_SHAPE_9_HIGH_RumbaDancing_1.fbx blended_output.fbx
# ...or
# RUN THE "command" SCRIPT DIRECTLY, DOUBLE CLICK:
#   runSynthAnthro_MeasureMesh.command

import re
import numpy as np
import sys

def extract_fbx_property_block(text, key):
    """Extracts a float array and its span from a named FBX block like 'Vertices' or 'Normals'."""
    pattern = re.compile(rf"{key}: \*\d+ \{{([\s\S]+?)\}}", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"{key} block not found")
    span = match.span(1)
    values = [float(v) for v in match.group(1).replace(',', ' ').split()]
    return np.array(values, dtype=np.float32), span

def extract_bone_transforms(text):
    """Returns a dictionary mapping bone names to their translation and rotation values and spans."""
    bone_pattern = re.compile(r'Model: "Model::([^"]+)", "LimbNode"\s*{([^}]+?Properties70: {[^}]+})', re.MULTILINE)
    prop_pattern = re.compile(r'P: "Lcl (Translation|Rotation)".+?A, ([^,\n]+), ([^,\n]+), ([^,\n]+)')

    bones = {}
    for match in bone_pattern.finditer(text):
        name = match.group(1)
        block = match.group(2)
        transforms = {}
        for p in prop_pattern.finditer(block):
            kind = p.group(1).lower()
            vec = np.array([float(p.group(i)) for i in range(2, 5)], dtype=np.float32)
            span = p.span(2)  # just the span of the first number
            transforms[kind] = (vec, span)
        bones[name] = transforms
    return bones

def replace_block(text, span, new_array):
    """Replaces a float array block with new values."""
    formatted = ", ".join(f"{v:.6f}" for v in new_array)
    return text[:span[0]] + formatted + text[span[1]:]

def replace_bone_values(text, bones1, bones2):
    """Averages bone transforms and replaces them in the original text."""
    result = text
    for name in bones1:
        if name in bones2:
            for key in ('translation', 'rotation'):
                if key in bones1[name] and key in bones2[name]:
                    v1, span = bones1[name][key]
                    v2, _ = bones2[name][key]
                    avg = (v1 + v2) / 2
                    new_line = f"{avg[0]:.6f}, {avg[1]:.6f}, {avg[2]:.6f}"
                    pre = result[:span[0]]
                    post = result[span[1]:]
                    result = pre + new_line + post
    return result

def average_ascii_fbx_with_bones(text1, text2):
    # Extract mesh geometry
    v1, v1_span = extract_fbx_property_block(text1, "Vertices")
    v2, _ = extract_fbx_property_block(text2, "Vertices")
    n1, n1_span = extract_fbx_property_block(text1, "Normals")
    n2, _ = extract_fbx_property_block(text2, "Normals")

    if v1.shape != v2.shape or n1.shape != n2.shape:
        raise ValueError("Vertex or normal arrays do not match in size")

    # Average mesh geometry
    avg_vertices = (v1 + v2) / 2
    avg_normals = (n1 + n2) / 2
    avg_normals = avg_normals.reshape(-1, 3)
    avg_normals /= np.linalg.norm(avg_normals, axis=1)[:, np.newaxis]
    avg_normals = avg_normals.flatten()

    # Replace in base text
    text1 = replace_block(text1, v1_span, avg_vertices)
    text1 = replace_block(text1, n1_span, avg_normals)

    # Extract and average bone transforms
    bones1 = extract_bone_transforms(text1)
    bones2 = extract_bone_transforms(text2)
    result = replace_bone_values(text1, bones1, bones2)

    return result

def main(fbx1_path, fbx2_path, output_path):
    with open(fbx1_path, 'r') as f:
        text1 = f.read()
    with open(fbx2_path, 'r') as f:
        text2 = f.read()

    result = average_ascii_fbx_with_bones(text1, text2)

    with open(output_path, 'w') as f:
        f.write(result)

    print(f"✅ Blended FBX saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python average_ascii_fbx_with_bones.py file1.fbx file2.fbx output.fbx")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])
