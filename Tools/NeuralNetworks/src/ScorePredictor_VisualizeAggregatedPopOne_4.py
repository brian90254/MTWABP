import os
import numpy as np
import pandas as pd
import cv2

# === CONFIGURATION ===
teams = ["SEA", "ATL"]
roles = ["Offense", "Defense"]
num_weeks = 6
matrix_size = (13, 13)
scale_factor = 25

popone_matrices = {}  # Will hold avg PopOne matrices like ("SEA", "Offense") → ndarray

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

def visualize_matrix(matrix, title, x_offset, y_offset):
    img = np.zeros((13 * scale_factor, 13 * scale_factor, 3), dtype=np.uint8)
    for y in range(13):
        for x in range(13):
            value = matrix[y, x]
            cx = x * scale_factor + scale_factor // 2
            cy = y * scale_factor + scale_factor // 2
            draw_cell(img, value, (cx, cy), radius=scale_factor // 2 - 2)

    cv2.namedWindow(title)
    cv2.imshow(title, img)
    cv2.moveWindow(title, x_offset, y_offset)

def load_and_average_popone(team, role):
    accumulator = np.zeros(matrix_size, dtype=float)
    valid_matrices = 0

    for week in range(1, num_weeks + 1):
        filename = f"Outputs/PopOne_{team}_{role}_week_{week}.csv"
        if os.path.exists(filename):
            try:
                matrix = pd.read_csv(filename, header=0).iloc[0:13, :].values
                if matrix.shape == matrix_size:
                    accumulator += matrix
                    valid_matrices += 1
                else:
                    print(f"Skipping {filename}: Incorrect shape {matrix.shape}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")
        else:
            print(f"File not found: {filename}")

    if valid_matrices == 0:
        print(f"No valid matrices found for {team}_{role}. Skipping.")
        return None

    avg_matrix = (accumulator / valid_matrices) * 2
    print(f"Loaded and averaged {valid_matrices} PopOne matrices for {team}_{role}.")
    return avg_matrix

# === Load and display base 2x2 visualizations ===
for i, team in enumerate(teams):
    for j, role in enumerate(roles):
        matrix = load_and_average_popone(team, role)
        if matrix is not None:
            popone_matrices[(team, role)] = matrix
            title = f"{team}_{role}_PopOne"
            x = 100 + 400 * j
            y = 100 + 400 * i
            visualize_matrix(matrix, title, x, y)

# === Add interaction visualizations to the right ===
# Interaction A: SEA_Defense × ATL_Offense
keyA = ("SEA", "Defense")
keyB = ("ATL", "Offense")
if keyA in popone_matrices and keyB in popone_matrices:
    interaction_AB = popone_matrices[keyA] * popone_matrices[keyB]
    visualize_matrix(interaction_AB, "SEA_Def x ATL_Off", 100 + 400 * 2, 100)

# Interaction B: SEA_Offense × ATL_Defense
keyC = ("SEA", "Offense")
keyD = ("ATL", "Defense")
if keyC in popone_matrices and keyD in popone_matrices:
    interaction_CD = popone_matrices[keyC] * popone_matrices[keyD]
    visualize_matrix(interaction_CD, "SEA_Off x ATL_Def", 100 + 400 * 2, 100 + 400)

print("Press any key to close all windows.")
cv2.waitKey(0)
cv2.destroyAllWindows()
