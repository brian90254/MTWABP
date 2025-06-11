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

def visualize_popone_avg(team, role):
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
        return

    avg_matrix = (accumulator / valid_matrices) * 2
    print(f"Loaded and averaged {valid_matrices} PopOne matrices for {team}_{role}.")

    img = np.zeros((13 * scale_factor, 13 * scale_factor, 3), dtype=np.uint8)
    for y in range(13):
        for x in range(13):
            value = avg_matrix[y, x]
            cx = x * scale_factor + scale_factor // 2
            cy = y * scale_factor + scale_factor // 2
            draw_cell(img, value, (cx, cy), radius=scale_factor // 2 - 2)

    window_name = f"{team}_{role}_PopOne"
    cv2.namedWindow(window_name)
    cv2.imshow(window_name, img)
    cv2.moveWindow(window_name, 100 + 400 * (0 if role == "Offense" else 1), 100 + 400 * (0 if team == "SEA" else 1))

# === Main Execution ===
for team in teams:
    for role in roles:
        visualize_popone_avg(team, role)

print("Press any key to close all windows.")
cv2.waitKey(0)
cv2.destroyAllWindows()
