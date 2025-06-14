import os
import numpy as np
import pandas as pd
import cv2
import sys

# === USAGE CHECK ===
if len(sys.argv) != 3:
    print("Usage: python3 visualize_popone.py <homeTeam> <awayTeam>")
    sys.exit(1)

home_team = sys.argv[1].upper()
away_team = sys.argv[2].upper()
teams = [home_team, away_team]

# === CONFIGURATION ===
roles = ["Offense", "Defense"]
num_weeks = 6
matrix_size = (13, 13)
scale_factor = 25
grid_spacing = 20

indicators = [
    "RushYds",
    "PassYds",
    "SackedYards",
    "Turnovers",
    "PenaltyYds",
    "TimeofPossession"
]

# === Functions ===
def load_average_matrix(team, role, indicator):
    accumulator = np.zeros(matrix_size, dtype=float)
    valid_matrices = 0
    for week in range(1, num_weeks + 1):
        filename = f"Outputs/PopOne_{team}_{role}_{indicator}_vs_Points_week_{week}.csv"
        if os.path.exists(filename):
            try:
                matrix = pd.read_csv(filename, header=0).iloc[0:13, :].values
                if matrix.shape == matrix_size:
                    accumulator += matrix
                    valid_matrices += 1
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    if valid_matrices == 0:
        return None
    return (accumulator * 2) / valid_matrices

def draw_cell(img, value, center, radius):
    val = value * 4
    if val <= 1:
        r, g, b = 0, int(val * 255), 255
    elif val <= 2:
        r, g, b = 0, 255, int((2 - val) * 255)
    elif val <= 3:
        r, g, b = int((val - 2) * 255), 255, 0
    elif val <= 4:
        r, g, b = 255, int((4 - val) * 255), 0
    else:
        r, g, b = 255, 0, 0
    cv2.circle(img, center, radius, (b, g, r), -1)

def visualize_matrix(matrix, title, offset_x, offset_y):
    img = np.zeros((13 * scale_factor, 13 * scale_factor, 3), dtype=np.uint8)
    for y in range(13):
        for x in range(13):
            value = matrix[y, x]
            cx = x * scale_factor + scale_factor // 2
            cy = y * scale_factor + scale_factor // 2
            draw_cell(img, value, (cx, cy), radius=scale_factor // 2 - 2)
    cv2.namedWindow(title)
    cv2.moveWindow(title, offset_x, offset_y)
    cv2.imshow(title, img)

def compute_centroid(matrix):
    total = np.sum(matrix)
    if total == 0:
        return (None, None)
    indices_y, indices_x = np.indices(matrix.shape)
    x_centroid = np.sum(indices_x * matrix) / total
    y_centroid = np.sum(indices_y * matrix) / total
    return (x_centroid, y_centroid)

# === Main Loop through indicators ===
for idx, indicator in enumerate(indicators):
    print(f"\n=== Visualizing Indicator: {indicator} ===")
    popone_matrices = {}

    for i, team in enumerate(teams):
        for j, role in enumerate(roles):
            avg_matrix = load_average_matrix(team, role, indicator)
            if avg_matrix is not None:
                key = f"{team}_{role}"
                popone_matrices[key] = avg_matrix
                visualize_matrix(avg_matrix, key, 100 + j * 400, 100 + i * 400)

    # Interaction A: Home Defense x Away Offense
    keyA = f"{home_team}_Defense"
    keyB = f"{away_team}_Offense"
    if keyA in popone_matrices and keyB in popone_matrices:
        interaction_AB = popone_matrices[keyA] * popone_matrices[keyB]
        visualize_matrix(interaction_AB, f"{home_team}_Def x {away_team}_Off", 100 + 400 * 2, 100)
        cx, cy = compute_centroid(interaction_AB)
        if cx is not None:
            print(f"Centroid {home_team}_Def x {away_team}_Off → X: {cx:.2f}, Y: {cy:.2f}")

    # Interaction B: Home Offense x Away Defense
    keyC = f"{home_team}_Offense"
    keyD = f"{away_team}_Defense"
    if keyC in popone_matrices and keyD in popone_matrices:
        interaction_CD = popone_matrices[keyC] * popone_matrices[keyD]
        visualize_matrix(interaction_CD, f"{home_team}_Off x {away_team}_Def", 100 + 400 * 2, 100 + 400)
        cx, cy = compute_centroid(interaction_CD)
        if cx is not None:
            print(f"Centroid {home_team}_Off x {away_team}_Def → X: {cx:.2f}, Y: {cy:.2f}")

    print("Press any key to continue to the next indicator.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
