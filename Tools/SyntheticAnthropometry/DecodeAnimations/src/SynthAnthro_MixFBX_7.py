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
    pattern = re.compile(rf"{key}: \*\d+ \{{([\s\S]+?)\}}", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None, None, False
    span = match.span(1)
    raw_data = match.group(1).strip()
    has_prefix = raw_data.startswith("a:")
    if has_prefix:
        raw_data = raw_data[2:].strip()
    values = [float(v) for v in raw_data.replace(',', ' ').split()]
    return np.array(values, dtype=np.float32), span, has_prefix

def extract_bone_transforms(text):
    bone_pattern = re.compile(r'Model: "Model::([^"]+)", "LimbNode"\s*{([^}]+?Properties70: {[^}]+})', re.MULTILINE)
    prop_pattern = re.compile(
        r'(P: "Lcl (Translation|Rotation)".+?A, )([^,\n]+), ([^,\n]+), ([^,\n]+)', re.MULTILINE
    )
    bones = {}
    for match in bone_pattern.finditer(text):
        name = match.group(1)
        block = match.group(2)
        transforms = {}
        for p in prop_pattern.finditer(block):
            kind = p.group(2).lower()
            vec = np.array([float(p.group(i)) for i in range(3, 6)], dtype=np.float32)
            span = (p.start(3), p.end(5))
            transforms[kind] = (vec, span)
        bones[name] = transforms
    return bones

def extract_bind_pose_matrices(text):
    pose_pattern = re.compile(r'PoseNode: \{([\s\S]+?)\}', re.MULTILINE)
    node_pattern = re.compile(r'Node: "Model::([^"]+)"')
    matrix_pattern = re.compile(r'Matrix: ([^\n]+)')

    matrices = {}
    for block in pose_pattern.finditer(text):
        block_text = block.group(1)
        node_match = node_pattern.search(block_text)
        matrix_match = matrix_pattern.search(block_text)
        if node_match and matrix_match:
            name = node_match.group(1)
            span = matrix_match.span(1)
            values = [float(x) for x in matrix_match.group(1).replace(',', ' ').split()]
            matrices[name] = (np.array(values, dtype=np.float32), span)
    return matrices

def replace_matrix_values(text, matrices1, matrices2):
    for name in matrices1:
        if name in matrices2:
            m1, span = matrices1[name]
            m2, _ = matrices2[name]
            avg = (m1 + m2) / 2
            new_line = ", ".join(f"{v:.6f}" for v in avg)
            text = text[:span[0]] + new_line + text[span[1]:]
    return text

def replace_block(text, span, new_array, values_per_line=10, add_prefix=True):
    lines = []
    for i in range(0, len(new_array), values_per_line):
        chunk = new_array[i:i + values_per_line]
        line = ", ".join(f"{v:.6f}" for v in chunk)
        lines.append(line)
    formatted = ",\n        ".join(lines)
    if add_prefix:
        formatted = "a: " + formatted
    if span:
        return text[:span[0]] + formatted + text[span[1]:]
    return text

def replace_bone_transforms(text, bones1, bones2):
    """Replace averaged Lcl Translation and Rotation across all common bones."""
    for name in bones1:
        if name in bones2:
            for key in ('translation', 'rotation'):
                if key in bones1[name] and key in bones2[name]:
                    v1, span = bones1[name][key]
                    v2, _ = bones2[name][key]
                    avg = (v1 + v2) / 2
                    new_line = f"{avg[0]:.6f}, {avg[1]:.6f}, {avg[2]:.6f}"
                    text = text[:span[0]] + new_line + text[span[1]:]
    return text

def average_ascii_fbx_with_bones(text_f, text_m):
    # Vertices
    v1, v1_span, v_prefix = extract_fbx_property_block(text_f, "Vertices")
    v2, _, _ = extract_fbx_property_block(text_m, "Vertices")
    avg_vertices = (v1 + v2) / 2
    text_f = replace_block(text_f, v1_span, avg_vertices, add_prefix=True)

    # Normals
    n1, n1_span, n_prefix = extract_fbx_property_block(text_f, "Normals")
    n2, _, _ = extract_fbx_property_block(text_m, "Normals")
    if n1 is not None and n2 is not None:
        avg_normals = (n1 + n2) / 2
    else:
        avg_normals = np.zeros_like(avg_vertices)
        avg_normals[2::3] = -1.0
        n1_span = None
    avg_normals = avg_normals.reshape(-1, 3)
    avg_normals /= np.linalg.norm(avg_normals, axis=1)[:, np.newaxis]
    avg_normals = avg_normals.flatten()
    text_f = replace_block(text_f, n1_span, avg_normals, add_prefix=True)

    # Lcl Transforms (Model blocks)
    bones_f = extract_bone_transforms(text_f)
    bones_m = extract_bone_transforms(text_m)
    text_f = replace_bone_transforms(text_f, bones_f, bones_m)

    # Bind Poses
    bind_f = extract_bind_pose_matrices(text_f)
    bind_m = extract_bind_pose_matrices(text_m)
    text_f = replace_matrix_values(text_f, bind_f, bind_m)

    return text_f

def main(fbx_female_path, fbx_male_path, output_path):
    with open(fbx_female_path, 'r', encoding='utf-8', errors='replace') as f:
        text_f = f.read()
    with open(fbx_male_path, 'r', encoding='utf-8', errors='replace') as f:
        text_m = f.read()

    result = average_ascii_fbx_with_bones(text_f, text_m)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"✅ Final blended FBX with averaged armature saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python average_ascii_fbx_with_bones.py FEMALE.fbx MALE.fbx output.fbx")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])
