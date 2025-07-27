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

# Placeholder script for Plan A: Build a minimal averaged FBX from scratch
# This code constructs a new FBX ASCII file from two Mixamo FBX inputs,
# averaging vertices, normals, skeleton transforms, and cluster weights
# while writing only the essential components: Models, Deformers, Clusters, Vertices, Normals, and Connections.

import re
import numpy as np
import sys

# Utilities for parsing

def extract_array_block(text, key):
    match = re.search(rf'{key}: \*\d+ \{{\s*a:([^}}]+)\}}', text)
    if not match:
        return None
    return np.array([float(x) for x in match.group(1).replace('\n', '').split(',')])

def extract_clusters(text):
    return dict(re.findall(r'(Deformer: "SubDeformer::([^\"]+)", "Cluster"\s*\{[\s\S]+?\})', text))

def extract_model_transforms(text):
    models = {}
    for match in re.finditer(r'Model: "Model::([^\"]+)", "LimbNode"\s*\{([\s\S]+?)\}', text):
        name = match.group(1)
        block = match.group(0)
        t = re.search(r'P: "Lcl Translation".*A, ([^,]+), ([^,]+), ([^\n]+)', block)
        r = re.search(r'P: "Lcl Rotation".*A, ([^,]+), ([^,]+), ([^\n]+)', block)
        translation = np.array([float(t.group(i)) for i in range(1, 4)]) if t else np.zeros(3)
        rotation = np.array([float(r.group(i)) for i in range(1, 4)]) if r else np.zeros(3)
        models[name] = (translation, rotation)
    return models

def average_models(models_f, models_m):
    avg = {}
    for name in set(models_f) & set(models_m):
        t_f, r_f = models_f[name]
        t_m, r_m = models_m[name]
        t_avg = (t_f + t_m) / 2
        r_avg = (r_f + r_m) / 2
        avg[name] = (t_avg, r_avg)
    return avg

def extract_weights(text):
    clusters = extract_clusters(text)
    weights = {}
    for name, block in clusters.items():
        idxs = re.search(r'Indexes: \*\d+ \{[^\}]*a: ([^\}]+)\}', block)
        vals = re.search(r'Weights: \*\d+ \{[^\}]*a: ([^\}]+)\}', block)
        if idxs and vals:
            i = [int(x) for x in idxs.group(1).replace('\n','').split(',')]
            w = [float(x) for x in vals.group(1).replace('\n','').split(',')]
            weights[name] = dict(zip(i, w))
    return weights

def average_weights(weights_f, weights_m):
    avg_weights = {}
    for name in set(weights_f) & set(weights_m):
        all_idx = set(weights_f[name]) | set(weights_m[name])
        avg_weights[name] = {i: (weights_f[name].get(i, 0)+weights_m[name].get(i, 0))/2 for i in all_idx}
    return avg_weights

# FBX output generator

def write_fbx(verts, norms, avg_models, avg_weights):
    lines = []
    lines.append("FBXHeaderExtension: {\n}")
    lines.append("Definitions:  {\n}")
    lines.append("  ObjectType: \"Model\" {\n    Count: %d\n  }\n}" % len(avg_models))
    lines.append("Objects:  {\n")

    for name, (t, r) in avg_models.items():
        lines.append(f"  Model: \"Model::{name}\", \"LimbNode\" {{")
        lines.append(f"    P: \"Lcl Translation\", \"Lcl Translation\", \"\", \"A\", {t[0]:.6f}, {t[1]:.6f}, {t[2]:.6f}")
        lines.append(f"    P: \"Lcl Rotation\", \"Lcl Rotation\", \"\", \"A\", {r[0]:.6f}, {r[1]:.6f}, {r[2]:.6f}")
        lines.append("  }")

    for bone, wmap in avg_weights.items():
        lines.append(f"  Deformer: \"SubDeformer::{bone}\", \"Cluster\" {{")
        lines.append(f"    Indexes: *{len(wmap)} {{ a: {','.join(map(str, wmap.keys()))} }}")
        lines.append(f"    Weights: *{len(wmap)} {{ a: {','.join(f'{v:.6f}' for v in wmap.values())} }}")
        lines.append("  }")

    lines.append("  Geometry: \"Geometry::Mesh\", \"Mesh\" {")
    lines.append(f"    Vertices: *{len(verts)} {{ a: {','.join(f'{v:.6f}' for v in verts)} }}")
    lines.append(f"    Normals: *{len(norms)} {{ a: {','.join(f'{v:.6f}' for v in norms)} }}")
    lines.append("  }")

    lines.append("}")  # End Objects
    lines.append("Connections: { }")
    return '\n'.join(lines)

# Main

def main(file1, file2, output):
    with open(file1, 'r', encoding='utf-8', errors='replace') as f:
        text1 = f.read()
    with open(file2, 'r', encoding='utf-8', errors='replace') as f:
        text2 = f.read()

    verts1 = extract_array_block(text1, "Vertices")
    verts2 = extract_array_block(text2, "Vertices")
    norms1 = extract_array_block(text1, "Normals")
    norms2 = extract_array_block(text2, "Normals")

    if verts1.shape != verts2.shape or norms1.shape != norms2.shape:
        raise ValueError("Vertex or normal mismatch")

    verts_avg = (verts1 + verts2) / 2
    norms_avg = (norms1 + norms2) / 2

    models1 = extract_model_transforms(text1)
    models2 = extract_model_transforms(text2)
    avg_models = average_models(models1, models2)

    weights1 = extract_weights(text1)
    weights2 = extract_weights(text2)
    avg_weights = average_weights(weights1, weights2)

    output_text = write_fbx(verts_avg, norms_avg, avg_models, avg_weights)

    with open(output, 'w', encoding='utf-8') as f:
        f.write(output_text)

    print(f"✅ Averaged FBX written to: {output}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py file1.fbx file2.fbx output.fbx")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
