# BRIAN COX copyright 2025

import numpy as np
import cv2
import time
import sys
import os
import pandas as pd
from collections import defaultdict
from itertools import combinations

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

# === Inputs ===
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
    global ClampOutputFlag, LearningFlag, InputUnitOne, InputUnitTwo, Nij, Wij, THij, quit_flag

    if len(sys.argv) != 4:
        print("Usage: python3 nn_sim.py <connectivity.txt> <weights.txt> <threshold.txt>")
        sys.exit(1)

    Nij = load_matrix(sys.argv[1], (NUM_NEURONS, NUM_NEURONS), int)
    Wij = load_matrix(sys.argv[2], (NUM_NEURONS, NUM_NEURONS), float)
    THij = np.genfromtxt(sys.argv[3], delimiter=",", dtype=float)

    try:
        scale_df = pd.read_csv("CSV/ScaleStats_1.csv", header=None, index_col=0)
        scale_dict = scale_df[1].to_dict()

        #team_files = [f.replace("_Offense.csv", "") for f in os.listdir("Aggregated") if f.endswith("_Offense.csv")]
        team_files = [f.replace("_Offense.csv", "") for f in os.listdir("TEST") if f.endswith("_Offense.csv")]

        for team in sorted(team_files):
            for role in ["Offense", "Defense"]:
                #stat_file = f"Aggregated/{team}_{role}.csv"
                stat_file = f"TEST/{team}_{role}.csv"
                if not os.path.exists(stat_file):
                    print(f"Missing file: {stat_file}")
                    continue

                df_stats = pd.read_csv(stat_file, index_col=0)
                all_weeks = [col for col in df_stats.columns if col.startswith("week_")]
                windows = init_windows()
                print(f"\n=== Processing {team} {role} ===")

                valid_stats = [row for row in df_stats.index if row.lower() not in ["", "bye", "name", "points"]]
                points_series = df_stats.loc["Points"]
                scalePoints = scale_dict.get("Points", 600)

                for statA in valid_stats:
                    current_week_index = 0
                    print(f"\n[INFO] Now processing stat: {statA} vs Points")
                    scaleA = scale_dict.get(statA, 1000)

                    while current_week_index < len(all_weeks) and not quit_flag:
                        week_col = all_weeks[current_week_index]
                        valA = df_stats.at[statA, week_col]
                        valB = df_stats.at["Points", week_col]

                        if str(valA).lower() != "bye" and str(valB).lower() != "bye":
                            if statA == "Time of Possession" and isinstance(valA, str) and ":" in valA:
                                valA = valA.split(":")[0]
                            if isinstance(valB, str) and ":" in valB:
                                valB = valB.split(":")[0]

                            InputUnitOne = (float(valA) / scaleA) + 0.3
                            InputUnitTwo = (float(valB) / scalePoints) + 0.3
                            # InputUnitOne = (float(valA) / scaleA) + 0.05
                            # InputUnitTwo = (float(valB) / scalePoints) + 0.05
                            print(f"[{week_col}] {statA}: {valA} → {InputUnitOne:.3f}, Points: {valB} → {InputUnitTwo:.3f}")

                            for _ in range(50):
                                update_network()
                                update_visuals(windows)
                                key = cv2.waitKey(20) & 0xFF
                                if key == 27:
                                    quit_flag = True
                                    break

                            out_path = f"Outputs/PopOne_{team}_{role}_{statA.replace(' ','')}_vs_Points_{week_col}.csv"
                            pop_vals = Vis_Ui[106:275].copy().reshape((13, 13))
                            pd.DataFrame(pop_vals).to_csv(out_path, index=False)
                            print(f"Saved → {out_path}")
                        # else:
                        #     print(f"[{week_col}] BYE week — skipping input")
                        else:
                            print(f"[{week_col}] BYE week — writing zeros")
                            out_path = f"Outputs/PopOne_{team}_{role}_{statA.replace(' ','')}_vs_Points_{week_col}.csv"
                            zero_matrix = np.zeros((13, 13))
                            pd.DataFrame(zero_matrix).to_csv(out_path, index=False)
                            print(f"Saved BYE week → {out_path}")


                        current_week_index += 1

    except Exception as e:
        print(f"Error during processing: {e}")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
