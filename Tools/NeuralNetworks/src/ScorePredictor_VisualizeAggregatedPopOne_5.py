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
grid_spacing = 20

# === Functions ===
def load_average_matrix(team, role):
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
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    if valid_matrices == 0:
        return None
    #return accumulator / valid_matrices
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
    window_title = title
    cv2.namedWindow(window_title)
    cv2.moveWindow(window_title, offset_x, offset_y)
    cv2.imshow(window_title, img)

def compute_centroid(matrix):
    total = np.sum(matrix)
    if total == 0:
        return (None, None)
    indices_y, indices_x = np.indices(matrix.shape)
    x_centroid = np.sum(indices_x * matrix) / total
    y_centroid = np.sum(indices_y * matrix) / total
    return (x_centroid, y_centroid)

# === Load and visualize each team-role combo ===
popone_matrices = {}
for i, team in enumerate(teams):
    for j, role in enumerate(roles):
        avg_matrix = load_average_matrix(team, role)
        if avg_matrix is not None:
            key = f"{team}_{role}"
            popone_matrices[key] = avg_matrix
            visualize_matrix(avg_matrix, key, 100 + j * 400, 100 + i * 400)

# === Interaction Visualizations ===
keyA = "SEA_Defense"
keyB = "ATL_Offense"
keyC = "SEA_Offense"
keyD = "ATL_Defense"

if keyA in popone_matrices and keyB in popone_matrices:
    interaction_AB = popone_matrices[keyA] * popone_matrices[keyB]
    visualize_matrix(interaction_AB, "SEA_Def x ATL_Off", 100 + 400 * 2, 100)
    cx, cy = compute_centroid(interaction_AB)
    if cx is not None:
        print(f"Centroid SEA_Def x ATL_Off → X: {cx:.2f}, Y: {cy:.2f}")

if keyC in popone_matrices and keyD in popone_matrices:
    interaction_CD = popone_matrices[keyC] * popone_matrices[keyD]
    visualize_matrix(interaction_CD, "SEA_Off x ATL_Def", 100 + 400 * 2, 100 + 400)
    cx, cy = compute_centroid(interaction_CD)
    if cx is not None:
        print(f"Centroid SEA_Off x ATL_Def → X: {cx:.2f}, Y: {cy:.2f}")

print("Press any key to close all windows.")
cv2.waitKey(0)
cv2.destroyAllWindows()
