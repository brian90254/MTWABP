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

# Mixamo hierarchy (simplified)
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

# ---------------- TRANSFORM MATH HELPERS ----------------
def euler_to_matrix(rot):
    rx, ry, rz = np.radians(rot)
    cx, cy, cz = np.cos([rx, ry, rz])
    sx, sy, sz = np.sin([rx, ry, rz])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
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

# ---------------- FBX EXTRACTORS ----------------
def extract_model_blocks(text):
    models = {}
    model_pattern = re.finditer(r'Model: "Model::([^"]+)", "LimbNode"\s*{([\s\S]+?)}\s*', text)
    for match in model_pattern:
        name, block = match.group(1), match.group(2)
        models[name] = {"block": block, "full_match": match, "text": match.group(0)}
    return models

def extract_lcl_transforms(model_text):
    props = {}
    for kind in ["Translation", "Rotation"]:
        match = re.search(rf'P: "Lcl {kind}".+?A, ([^,\n]+), ([^,\n]+), ([^,\n]+)', model_text)
        if match:
            vec = np.array([float(match.group(i)) for i in range(1, 4)])
            props[kind.lower()] = vec
    return props

def resolve_shortnames(models):
    return {name.split(":")[-1]: name for name in models}

def compute_global_transforms(models, name_map):
    globals = {}
    for short_name, parent_short in mixamo_hierarchy.items():
        long_name = name_map.get(short_name)
        if not long_name or long_name not in models:
            continue
        props = extract_lcl_transforms(models[long_name]["block"])
        local = compose_matrix(props.get("translation", np.zeros(3)), props.get("rotation", np.zeros(3)))
        if parent_short:
            parent = name_map.get(parent_short)
            if parent in globals:
                globals[long_name] = globals[parent] @ local
            else:
                globals[long_name] = local
        else:
            globals[long_name] = local
    return globals

# ---------------- MAIN REPLACEMENT FUNCTION ----------------
def average_jointspace_and_replace(text_f, text_m):
    models_f = extract_model_blocks(text_f)
    models_m = extract_model_blocks(text_m)

    map_f = resolve_shortnames(models_f)
    map_m = resolve_shortnames(models_m)

    globals_f = compute_global_transforms(models_f, map_f)
    globals_m = compute_global_transforms(models_m, map_m)

    out_text = text_f  # Start from FEMALE

    for short_name, parent in mixamo_hierarchy.items():
        bone_f = map_f.get(short_name)
        bone_m = map_m.get(short_name)
        if bone_f and bone_m and bone_f in globals_f and bone_m in globals_m:
            avg_mat = (globals_f[bone_f] + globals_m[bone_m]) / 2
            t_avg, r_avg = decompose_matrix(avg_mat)

            # Replace Lcl Translation
            out_text = re.sub(
                rf'(Model: "Model::{bone_f}".+?P: "Lcl Translation".+?A, )[^,\n]+, [^,\n]+, [^,\n]+',
                rf'\1{t_avg[0]:.6f}, {t_avg[1]:.6f}, {t_avg[2]:.6f}',
                out_text,
                flags=re.DOTALL
            )
            # Replace Lcl Rotation
            out_text = re.sub(
                rf'(Model: "Model::{bone_f}".+?P: "Lcl Rotation".+?A, )[^,\n]+, [^,\n]+, [^,\n]+',
                rf'\1{r_avg[0]:.6f}, {r_avg[1]:.6f}, {r_avg[2]:.6f}',
                out_text,
                flags=re.DOTALL
            )

    return out_text

# ---------------- CLI WRAPPER ----------------
def main(female_fbx_path, male_fbx_path, output_path):
    with open(female_fbx_path, "r", encoding="utf-8", errors="replace") as f:
        text_f = f.read()
    with open(male_fbx_path, "r", encoding="utf-8", errors="replace") as f:
        text_m = f.read()

    new_text = average_jointspace_and_replace(text_f, text_m)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"✅ Output written to {output_path} with averaged joint space.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python average_ascii_fbx_jointspace.py FEMALE.fbx MALE.fbx output.fbx")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
