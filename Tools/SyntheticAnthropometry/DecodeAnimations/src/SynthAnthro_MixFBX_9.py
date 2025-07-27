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

# Define Mixamo hierarchy (short names only)
mixamo_hierarchy = {
    "Hips": None,
    "Spine": "Hips",
    "Spine1": "Spine",
    "Spine2": "Spine1",
    "Neck": "Spine2",
    "Head": "Neck",
    "LeftShoulder": "Spine2",
    "LeftArm": "LeftShoulder",
    "LeftForeArm": "LeftArm",
    "LeftHand": "LeftForeArm",
    "RightShoulder": "Spine2",
    "RightArm": "RightShoulder",
    "RightForeArm": "RightArm",
    "RightHand": "RightForeArm",
    "LeftUpLeg": "Hips",
    "LeftLeg": "LeftUpLeg",
    "LeftFoot": "LeftLeg",
    "RightUpLeg": "Hips",
    "RightLeg": "RightUpLeg",
    "RightFoot": "RightLeg",
}

# --- Matrix helpers ---
def euler_to_matrix(rot):
    rx, ry, rz = np.radians(rot)
    cx, cy, cz = np.cos([rx, ry, rz])
    sx, sy, sz = np.sin([rx, ry, rz])
    Rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    Rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    return Rz @ Ry @ Rx

def compose_matrix(translation, rotation):
    mat = np.eye(4)
    mat[:3, :3] = euler_to_matrix(rotation)
    mat[:3, 3] = translation
    return mat

def decompose_matrix(matrix):
    translation = matrix[:3, 3]
    R = matrix[:3, :3]
    sy = np.linalg.norm([R[0,0], R[1,0]])
    if sy > 1e-6:
        x = np.arctan2(R[2,1], R[2,2])
        y = np.arctan2(-R[2,0], sy)
        z = np.arctan2(R[1,0], R[0,0])
    else:
        x = np.arctan2(-R[1,2], R[1,1])
        y = np.arctan2(-R[2,0], sy)
        z = 0
    return translation, np.degrees([x, y, z])

# --- FBX extractors ---
def extract_model_blocks(text):
    models = {}
    for match in re.finditer(r'Model: "Model::([^"]+)", "LimbNode"\s*{([\s\S]+?)}', text):
        name, block = match.group(1), match.group(2)
        models[name] = {"block": block, "text": match.group(0)}
    return models

def resolve_shortnames(models):
    return {name.split(":")[-1]: name for name in models}

def extract_lcl_transforms(model_text):
    props = {}
    for kind in ["Translation", "Rotation"]:
        m = re.search(rf'P: "Lcl {kind}".+?A, ([^,\n]+), ([^,\n]+), ([^,\n]+)', model_text)
        if m:
            props[kind.lower()] = np.array([float(m.group(i)) for i in range(1, 4)])
    return props

def compute_global_transforms(models, name_map):
    globals = {}
    for short, parent in mixamo_hierarchy.items():
        name = name_map.get(short)
        if not name or name not in models:
            continue
        props = extract_lcl_transforms(models[name]["block"])
        local = compose_matrix(props.get("translation", np.zeros(3)), props.get("rotation", np.zeros(3)))
        if parent:
            parent_name = name_map.get(parent)
            if parent_name in globals:
                globals[name] = globals[parent_name] @ local
            else:
                globals[name] = local
        else:
            globals[name] = local
    return globals

# --- Replace skeleton transforms ---
def average_skeleton_transforms(text_f, text_m):
    models_f = extract_model_blocks(text_f)
    models_m = extract_model_blocks(text_m)
    map_f = resolve_shortnames(models_f)
    map_m = resolve_shortnames(models_m)

    globals_f = compute_global_transforms(models_f, map_f)
    globals_m = compute_global_transforms(models_m, map_m)

    output_text = text_f
    for short_name in mixamo_hierarchy:
        name_f = map_f.get(short_name)
        name_m = map_m.get(short_name)
        if name_f and name_m and name_f in globals_f and name_m in globals_m:
            avg_mat = (globals_f[name_f] + globals_m[name_m]) / 2
            t_avg, r_avg = decompose_matrix(avg_mat)

            # Replace Lcl Translation
            output_text = re.sub(
                rf'(Model: "Model::{re.escape(name_f)}".+?P: "Lcl Translation".+?A, )[^,\n]+, [^,\n]+, [^,\n]+',
                rf'\1{t_avg[0]:.6f}, {t_avg[1]:.6f}, {t_avg[2]:.6f}',
                output_text, flags=re.DOTALL
            )
            # Replace Lcl Rotation
            output_text = re.sub(
                rf'(Model: "Model::{re.escape(name_f)}".+?P: "Lcl Rotation".+?A, )[^,\n]+, [^,\n]+, [^,\n]+',
                rf'\1{r_avg[0]:.6f}, {r_avg[1]:.6f}, {r_avg[2]:.6f}',
                output_text, flags=re.DOTALL
            )
    return output_text

# --- Replace vertex/normals blocks ---
def extract_float_array_block(text, key):
    match = re.search(rf'{key}: \*([0-9]+) \{{\s*a:\s*([^\}}]+)\s*\}}', text)
    if not match:
        return None
    floats = [float(x) for x in match.group(2).replace('\n', '').split(',')]
    return np.array(floats)

def replace_float_array_block(text, key, new_array):
    new_str = ','.join(f"{v:.6f}" for v in new_array)
    # return re.sub(rf'({key}: \*\d+ \{{\s*a:\s*)[^\}}]+(\s*\}})',
    #               rf'\1{new_str}\2', text)
    pattern = rf'({key}: \*\d+ \{{\s*a:\s*)([^\}}]+)(\s*\}})'
    replacement = lambda m: f'{m.group(1)}{new_str}{m.group(3)}'
    return re.sub(pattern, replacement, text)


# --- Main logic ---
def main(female_file, male_file, output_file):
    with open(female_file, "r", encoding="utf-8", errors="replace") as f:
        text_f = f.read()
    with open(male_file, "r", encoding="utf-8", errors="replace") as f:
        text_m = f.read()

    # Average mesh
    verts_f = extract_float_array_block(text_f, "Vertices")
    verts_m = extract_float_array_block(text_m, "Vertices")
    norms_f = extract_float_array_block(text_f, "Normals")
    norms_m = extract_float_array_block(text_m, "Normals")

    verts_avg = (verts_f + verts_m) / 2 if verts_f is not None else None
    norms_avg = (norms_f + norms_m) / 2 if norms_f is not None else None

    output_text = average_skeleton_transforms(text_f, text_m)

    if verts_avg is not None:
        output_text = replace_float_array_block(output_text, "Vertices", verts_avg)
    if norms_avg is not None:
        output_text = replace_float_array_block(output_text, "Normals", norms_avg)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"✅ Averaged FBX written to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python average_ascii_fbx_full.py FEMALE.fbx MALE.fbx output.fbx")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
