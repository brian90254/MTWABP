# BRIAN COX copyright 2025

import numpy as np
import cv2
import time
import sys
import os
import pandas as pd
from collections import defaultdict

# === CONFIGURATION ===
NUM_NEURONS = 328
NUM_INPUTS = 54
SCALE_FACTOR = 25
S_F = SCALE_FACTOR
PLASTICITY = False
NORMALIZATION_FACTOR = 11
FEEDBACK_RATIO = 0.2
THRESHOLD_VALUE = 0.65
LEARNING_RATE = 0.1
DECAY_EPSILON = 0.01

# === FLAGS ===
ClampOutputFlag = False
LearningFlag = True
quit_flag = False

# === Neural arrays ===
Nij = np.zeros((NUM_NEURONS, NUM_NEURONS))
Wij = np.zeros((NUM_NEURONS, NUM_NEURONS))
THij = np.zeros(NUM_NEURONS)
Ui = np.zeros(NUM_NEURONS)
Vi = np.zeros(NUM_NEURONS)
Yi = np.zeros(NUM_NEURONS)
OMi = np.full(NUM_NEURONS, THRESHOLD_VALUE)
Vis_Ui = np.zeros(NUM_NEURONS)
Neur_Ui = np.zeros(NUM_NEURONS)

InputUnitOne, InputUnitTwo = 0.1, 0.1

# === File Parsing ===
def load_matrix(filename, shape, dtype=float):
    data = np.genfromtxt(filename, delimiter=",", dtype=dtype)
    mat = np.zeros(shape, dtype=dtype)
    rows, cols = data.shape
    mat[:rows, :cols] = data
    return mat

# === Visualization Drawing ===
def draw_neuron_circle(img, value, center, radius):
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

# === Initialize Windows ===
def init_windows():
    windows = {}
    layout = {
        "UnitOne":  (0, 0),
        "UnitTwo":  (320, 0),
        "GaussOne": (0, 240),
        "GaussTwo": (360, 240),
        "PopOne":   (160, 480),
    }
    for name, (x, y) in layout.items():
        size = (3 * S_F, 3 * S_F) if "Unit" in name else (13 * S_F, 4 * S_F if "Gauss" in name else 13 * S_F)
        windows[name] = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        cv2.namedWindow(name)
        cv2.moveWindow(name, x, y)
    return windows

# === Network Update ===
def update_network():
    global Ui, Vi, Yi, Wij, THij, OMi

    Ui[0], Ui[53] = Vis_Ui[0], Vis_Ui[53]
    Vi[:] = np.sum(Ui[None, :] * Wij * ((Nij == 1) | (Nij == -1)), axis=1)
    Yi[:] = 1 / (1 + np.exp((THij - Vi) * 0.98))

    if PLASTICITY and LearningFlag:
        for i in range(NUM_NEURONS):
            for j in range(NUM_NEURONS):
                if i > j and Nij[i, j] == 1:
                    thetaY = min((Yi[i] - OMi[i]), 1) if Yi[i] > (OMi[i] / 2) else -Yi[i]
                    deltaW = (thetaY * Ui[j] - DECAY_EPSILON * Wij[i, j]) * LEARNING_RATE
                    Wij[i, j] = max(0, Wij[i, j] + deltaW)
                    Wij[j, i] = Wij[i, j] * FEEDBACK_RATIO

        for i in range(NUM_NEURONS):
            total = np.sum(Wij[i, :] * (Nij[i, :] == 1))
            if total > 0:
                Wij[i, :] = Wij[i, :] / (total / NORMALIZATION_FACTOR)
                Wij[j, i] = Wij[i, j] * FEEDBACK_RATIO

    Ui = 0.9 * Yi + 0.1 * Ui
    Neur_Ui[:] = Ui
    Vis_Ui[:] = Ui

# === Visual Update ===
def update_visuals(windows):
    global InputUnitOne, InputUnitTwo
    Vis_Ui[0], Vis_Ui[53] = InputUnitOne, InputUnitTwo
    Neur_Ui[0], Neur_Ui[53] = InputUnitOne, InputUnitTwo

    for img in windows.values():
        img.fill(0)

    draw_neuron_circle(windows["UnitOne"], Vis_Ui[0], (38, 38), 30)
    draw_neuron_circle(windows["UnitTwo"], Vis_Ui[53], (38, 38), 30)

    for i in range(52):
        y, x = divmod(i, 13)
        center = (x * S_F + 13, y * S_F + 13)
        draw_neuron_circle(windows["GaussOne"], Vis_Ui[i + 1], center, 10)
        draw_neuron_circle(windows["GaussTwo"], Vis_Ui[i + 54], center, 10)

    for i in range(169):
        y, x = divmod(i, 13)
        center = (x * S_F + 13, y * S_F + 13)
        draw_neuron_circle(windows["PopOne"], Vis_Ui[i + 106], center, 10)

    for name, img in windows.items():
        cv2.imshow(name, img)

# === Main Function ===
def main():
    global ClampOutputFlag, LearningFlag, InputUnitOne, InputUnitTwo, Nij, Wij, THij

    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print("Usage: python3 nn_sim.py <connectivity.txt> <weights.txt> <threshold.txt>")
        sys.exit(1)

    Nij = load_matrix(sys.argv[1], (NUM_NEURONS, NUM_NEURONS), int)
    Wij = load_matrix(sys.argv[2], (NUM_NEURONS, NUM_NEURONS), float)
    THij = np.genfromtxt(sys.argv[3], delimiter=",", dtype=float)

    # === Load stats from Aggregated/DEN_Offense.csv ===
    loop_count = 0
    current_week_index = 0

    team = "DEN"
    role = "Defense"
    stat_file = f"Aggregated/{team}_{role}.csv"

    try:
        df_stats = pd.read_csv(stat_file, index_col=0)
        all_weeks = [col for col in df_stats.columns if col.startswith("week_")]

        # === Initialize with week_1 ===
        rush_yds = df_stats.at["Rush Yds", all_weeks[0]]
        points = df_stats.at["Points", all_weeks[0]]
        if str(rush_yds).lower() != "bye" and str(points).lower() != "bye":
            InputUnitOne = (float(rush_yds) / 300.0) + 0.15
            InputUnitTwo = (float(points) / 50.0) + 0.15
            print(f"Rush Yds: {rush_yds} → InputUnitOne = {InputUnitOne:.4f}")
            print(f"Points: {points} → InputUnitTwo = {InputUnitTwo:.4f}")
        else:
            print(f"{all_weeks[0]} is a bye week — using default input values.")

        # Only advance index once here to avoid re-using week_1
        current_week_index = 1

    except Exception as e:
        print(f"Error loading {stat_file}: {e}")
        df_stats = None
        all_weeks = []

    print("Files loaded. Starting simulation.")
    windows = init_windows()

    while not quit_flag:
        update_network()
        update_visuals(windows)
        loop_count += 1

        if loop_count % 100 == 0 and df_stats is not None and current_week_index < len(all_weeks):
            week_col = all_weeks[current_week_index]
            rush_yds = df_stats.at["Rush Yds", week_col]
            points = df_stats.at["Points", week_col]

            if str(rush_yds).lower() != "bye" and str(points).lower() != "bye":
                InputUnitOne = (float(rush_yds) / 300.0) + 0.15
                InputUnitTwo = (float(points) / 50.0) + 0.15
                print(f"\n--- Loop {loop_count}: Using {week_col} stats ---")
                print(f"Rush Yds: {rush_yds} → InputUnitOne = {InputUnitOne:.4f}")
                print(f"Points: {points} → InputUnitTwo = {InputUnitTwo:.4f}")
            else:
                print(f"\n--- Loop {loop_count}: {week_col} is a bye week ---")

            try:
                pop_vals = Vis_Ui[106:275].copy()
                pop_matrix = pop_vals.reshape((13, 13))
                df_pop = pd.DataFrame(pop_matrix)
                os.makedirs("Outputs", exist_ok=True)
                out_path = f"Outputs/PopOne_{team}_{role}_{week_col}.csv"
                df_pop.to_csv(out_path, index=False)
                print(f"Saved PopOne activations to {out_path}")
            except Exception as e:
                print(f"Error saving PopOne activations: {e}")

            current_week_index += 1

        key = cv2.waitKey(100) & 0xFF
        if key == 27: break
        elif key in (ord('w'), ord('W')): print("=== WEIGHTS ===\n", Wij)
        elif key in (ord('c'), ord('C')): ClampOutputFlag = not ClampOutputFlag
        elif key in (ord('l'), ord('L')): LearningFlag = not LearningFlag
        elif key in (ord('u'), ord('U')): InputUnitTwo = min(0.95, InputUnitTwo + 0.025)
        elif key in (ord('n'), ord('N')): InputUnitTwo = max(0.05, InputUnitTwo - 0.025)
        elif key in (ord('t'), ord('T')): InputUnitOne = min(0.95, InputUnitOne + 0.025)
        elif key in (ord('v'), ord('V')): InputUnitOne = max(0.05, InputUnitOne - 0.025)
        elif key == 1: InputUnitOne = min(0.95, InputUnitOne + 0.025)
        elif key == 0: InputUnitOne = max(0.05, InputUnitOne - 0.025)
        elif key == 3: InputUnitTwo = min(0.95, InputUnitTwo + 0.025)
        elif key == 2: InputUnitTwo = max(0.05, InputUnitTwo - 0.025)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
