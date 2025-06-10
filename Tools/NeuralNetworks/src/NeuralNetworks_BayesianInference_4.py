# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
# COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# IF NEEDED, ACTIVATE THE VENV:
#   source venv39/bin/activate
# THEN RUN THE CODE IN "src" AND PASS ARGUMENTS FROM "CSV":
#   python src/NeuralNetworks_BayesianInference_4.py CSV/ConnectivityMatrix_1.csv CSV/WeightMatrix_1.csv CSV/ThresholdMatrix_1.csv
# ----------------------------

import numpy as np
import cv2
import time
import sys

# === CONFIGURATION ===
NUM_NEURONS = 328
NUM_INPUTS = 54
SCALE_FACTOR = 25
S_F = SCALE_FACTOR
PLASTICITY = False  # Enable for BCM + normalization
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

# === Initialize Visualization Windows ===
# def init_windows():
#     windows = {}
#     for name in ["UnitOne", "UnitTwo", "GaussOne", "GaussTwo", "PopOne"]:
#         size = (3 * S_F, 3 * S_F) if "Unit" in name else (13 * S_F, 4 * S_F if "Gauss" in name else 13 * S_F)
#         windows[name] = np.zeros((size[1], size[0], 3), dtype=np.uint8)
#         cv2.namedWindow(name)
#     return windows

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


# === Neural Update Step ===
def update_network():
    global Ui, Vi, Yi, Wij, THij, OMi

    Ui[0], Ui[53] = Vis_Ui[0], Vis_Ui[53]
    Vi[:] = np.sum(Ui[None, :] * Wij * ((Nij == 1) | (Nij == -1)), axis=1)
    Yi[:] = 1 / (1 + np.exp((THij - Vi) * 0.98))

    if PLASTICITY and LearningFlag:
        for i in range(NUM_NEURONS):
            for j in range(NUM_NEURONS):
                if i > j and Nij[i, j] == 1:
                    if Yi[i] > (OMi[i] / 2):
                        thetaY = min((Yi[i] - OMi[i]), 1)
                    else:
                        thetaY = -Yi[i]
                    deltaW = (thetaY * Ui[j] - DECAY_EPSILON * Wij[i, j]) * LEARNING_RATE
                    Wij[i, j] = max(0, Wij[i, j] + deltaW)
                    Wij[j, i] = Wij[i, j] * FEEDBACK_RATIO

        # Normalize weights
        for i in range(NUM_NEURONS):
            total = np.sum(Wij[i, :] * (Nij[i, :] == 1))
            if total > 0:
                Wij[i, :] = Wij[i, :] / (total / NORMALIZATION_FACTOR)
                Wij[j, i] = Wij[i, j] * FEEDBACK_RATIO

    # Persistence
    Ui = 0.9 * Yi + 0.1 * Ui
    Neur_Ui[:] = Ui
    Vis_Ui[:] = Ui

# === Visualization Update ===
def update_visuals(windows):
    global InputUnitOne, InputUnitTwo
    Vis_Ui[0] = InputUnitOne
    Vis_Ui[53] = InputUnitTwo
    Neur_Ui[0], Neur_Ui[53] = Vis_Ui[0], Vis_Ui[53]

    # Clear images
    for img in windows.values():
        img.fill(0)

    draw_neuron_circle(windows["UnitOne"], Vis_Ui[0], (38, 38), 30)
    draw_neuron_circle(windows["UnitTwo"], Vis_Ui[53], (38, 38), 30)

    # GaussOne: neurons 1–52
    for i in range(52):
        y, x = divmod(i, 13)
        center = (x * S_F + 13, y * S_F + 13)
        draw_neuron_circle(windows["GaussOne"], Vis_Ui[i + 1], center, 10)

    # GaussTwo: neurons 54–105
    for i in range(52):
        y, x = divmod(i, 13)
        center = (x * S_F + 13, y * S_F + 13)
        draw_neuron_circle(windows["GaussTwo"], Vis_Ui[i + 54], center, 10)

    # PopOne: neurons 106–274
    for i in range(169):
        y, x = divmod(i, 13)
        center = (x * S_F + 13, y * S_F + 13)
        draw_neuron_circle(windows["PopOne"], Vis_Ui[i + 106], center, 10)

    for name, img in windows.items():
        cv2.imshow(name, img)

# === MAIN LOOP ===
def main():
    global ClampOutputFlag, LearningFlag, InputUnitOne, InputUnitTwo, Nij, Wij, THij

    if len(sys.argv) != 4:
        print("Usage: python3 nn_sim.py <connectivity.txt> <weights.txt> <threshold.txt>")
        sys.exit(1)

    Nij = load_matrix(sys.argv[1], (NUM_NEURONS, NUM_NEURONS), int)
    Wij = load_matrix(sys.argv[2], (NUM_NEURONS, NUM_NEURONS), float)
    #THij = load_matrix(sys.argv[3], (NUM_NEURONS,), float)
    THij = np.genfromtxt(sys.argv[3], delimiter=",", dtype=float)


    print("Files loaded. Starting simulation.")
    windows = init_windows()

    while not quit_flag:
        update_network()
        update_visuals(windows)

        key = cv2.waitKey(100) & 0xFF
        #print(f"Key code: {key}")
        if key == 27:  # ESC
            break
        elif key in (ord('w'), ord('W')):
            print("=== WEIGHTS ===")
            print(Wij)
        elif key in (ord('c'), ord('C')):
            ClampOutputFlag = not ClampOutputFlag
        elif key in (ord('l'), ord('L')):
            LearningFlag = not LearningFlag
        elif key in (ord('u'), ord('U')):
            InputUnitTwo = min(0.95, InputUnitTwo + 0.025)
        elif key in (ord('n'), ord('N')):
            InputUnitTwo = max(0.05, InputUnitTwo - 0.025)
        elif key in (ord('t'), ord('T')):
            InputUnitOne = min(0.95, InputUnitOne + 0.025)
        elif key in (ord('v'), ord('V')):
            InputUnitOne = max(0.05, InputUnitOne - 0.025)
        # ------------------------------------------------
        # ADDED ARROW KEYS TO MOVE INPUT GAUSSIAMS
        elif key == 1:  # Up arrow
            InputUnitOne = min(0.95, InputUnitOne + 0.025)
        elif key == 0:  # Down arrow
            InputUnitOne = max(0.05, InputUnitOne - 0.025)
        elif key == 3:  # Right arrow
            InputUnitTwo = min(0.95, InputUnitTwo + 0.025)
        elif key == 2:  # Left arrow
            InputUnitTwo = max(0.05, InputUnitTwo - 0.025)
        # ------------------------------------------------
 
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
