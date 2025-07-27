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

# --- Mixamo hierarchy (short names only) ---
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

# --- FBX parsers ---
def extract_model_blocks(text):
    models = {}
    for match in re.finditer(r'Model: "Model::([^"]+)", "LimbNode"\s*{([\s\S]+?)}', text):
        name, block = match.group(1), match.group(0)
        models[name] = {"block": block}
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
        if not (name_f and name_m): continue
        if not (name_f in globals_f and name_m in globals_m): continue

        avg_mat = (globals_f[name_f] + globals_m[name_m]) / 2
        t_avg, r_avg = decompose_matrix(avg_mat)

        block_f = models_f[name_f]["block"]
        new_block = re.sub(
            r'P: "Lcl Translation".+?A, [^,\n]+, [^,\n]+, [^,\n]+',
            f'P: "Lcl Translation", "Lcl Translation", "", "A", {t_avg[0]:.6f}, {t_avg[1]:.6f}, {t_avg[2]:.6f}',
            block_f
        )
        new_block = re.sub(
            r'P: "Lcl Rotation".+?A, [^,\n]+, [^,\n]+, [^,\n]+',
            f'P: "Lcl Rotation", "Lcl Rotation", "", "A", {r_avg[0]:.6f}, {r_avg[1]:.6f}, {r_avg[2]:.6f}',
            new_block
        )
        output_text = output_text.replace(block_f, new_block)

    return output_text

def extract_float_array_block(text, key):
    match = re.search(rf'{key}: \*([0-9]+) \{{\s*a:\s*([^\}}]+)\s*\}}', text)
    if not match:
        return None
    floats = [float(x) for x in match.group(2).replace('\n', '').split(',')]
    return np.array(floats)

def replace_float_array_block(text, key, new_array):
    new_str = ','.join(f"{v:.6f}" for v in new_array)
    pattern = rf'({key}: \*\d+ \{{\s*a:\s*)([^\}}]+)(\s*\}})'
    replacement = lambda m: f'{m.group(1)}{new_str}{m.group(3)}'
    return re.sub(pattern, replacement, text)

def average_cluster_blocks(text_f, text_m):
    clusters_f = dict(re.findall(r'(Deformer: "SubDeformer::([^"]+)", "Cluster"\s*{[\s\S]+?})', text_f))
    clusters_m = dict(re.findall(r'(Deformer: "SubDeformer::([^"]+)", "Cluster"\s*{[\s\S]+?})', text_m))
    output_text = text_f

    for name in set(clusters_f) & set(clusters_m):
        block_f = clusters_f[name]
        block_m = clusters_m[name]

        def extract_matrix(text, label):
            match = re.search(rf'{label}: \*16 \{{\s*a:\s*([^\}}]+)\s*\}}', text)
            if match:
                vals = [float(v) for v in match.group(1).replace('\n', '').split(',')]
                return np.array(vals).reshape(4, 4)
            return None

        def extract_array(text, label, int_cast=False):
            match = re.search(rf'{label}: \*\d+ \{{[\s\S]*?a:\s*([^\}}]+)\}}', text)
            if not match: return []
            vals = match.group(1).replace('\n', '').split(',')
            return [int(v) if int_cast else float(v) for v in vals]

        tf_f = extract_matrix(block_f, "Transform")
        tf_m = extract_matrix(block_m, "Transform")
        tfl_f = extract_matrix(block_f, "TransformLink")
        tfl_m = extract_matrix(block_m, "TransformLink")
        idx_f = extract_array(block_f, "Indexes", int_cast=True)
        idx_m = extract_array(block_m, "Indexes", int_cast=True)
        wts_f = extract_array(block_f, "Weights")
        wts_m = extract_array(block_m, "Weights")

        tf_avg = (tf_f + tf_m) / 2
        tfl_avg = (tfl_f + tfl_m) / 2

        idx_all = sorted(set(idx_f) | set(idx_m))
        map_f = dict(zip(idx_f, wts_f))
        map_m = dict(zip(idx_m, wts_m))
        wts_avg = [(map_f.get(i, 0.0) + map_m.get(i, 0.0)) / 2 for i in idx_all]

        tf_str = ','.join(f"{v:.6f}" for v in tf_avg.flatten())
        tfl_str = ','.join(f"{v:.6f}" for v in tfl_avg.flatten())
        idx_str = ','.join(str(i) for i in idx_all)
        wts_str = ','.join(f"{v:.6f}" for v in wts_avg)

        new_block = re.sub(r'Transform: \*16 \{[\s\S]*?a: [^\}]+\}',
            f'''Transform: *16 {{
        a: {tf_str}}}''', block_f)

        new_block = re.sub(r'TransformLink: \*16 \{[\s\S]*?a: [^\}]+\}',
            f'''TransformLink: *16 {{
        a: {tfl_str}}}''', new_block)

        new_block = re.sub(r'Indexes: \*\d+ \{[\s\S]*?a: [^\}]+\}',
            f'''Indexes: *{len(idx_all)} {{
        a: {idx_str}}}''', new_block)

        new_block = re.sub(r'Weights: \*\d+ \{[\s\S]*?a: [^\}]+\}',
            f'''Weights: *{len(wts_avg)} {{
        a: {wts_str}}}''', new_block)

        output_text = output_text.replace(block_f, new_block)

    return output_text

def main(female_file, male_file, output_file):
    with open(female_file, "r", encoding="utf-8", errors="replace") as f:
        text_f = f.read()
    with open(male_file, "r", encoding="utf-8", errors="replace") as f:
        text_m = f.read()

    verts_f = extract_float_array_block(text_f, "Vertices")
    verts_m = extract_float_array_block(text_m, "Vertices")
    norms_f = extract_float_array_block(text_f, "Normals")
    norms_m = extract_float_array_block(text_m, "Normals")

    if verts_f.shape != verts_m.shape:
        raise ValueError("Vertex arrays do not match in size.")
    if norms_f.shape != norms_m.shape:
        raise ValueError("Normal arrays do not match in size.")

    verts_avg = (verts_f + verts_m) / 2
    norms_avg = (norms_f + norms_m) / 2

    output_text = average_skeleton_transforms(text_f, text_m)
    output_text = replace_float_array_block(output_text, "Vertices", verts_avg)
    output_text = replace_float_array_block(output_text, "Normals", norms_avg)
    output_text = average_cluster_blocks(text_f, text_m)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"✅ Averaged FBX written to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py FEMALE.fbx MALE.fbx output.fbx")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
