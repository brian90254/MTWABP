# neural_sim_visualizer.py

import cv2
import numpy as np
import time
import threading

# Constants and configuration
INPUT_LAYER = 5
NUM_NEURONS = 328
SCALE_FACTOR = 18
S_F = SCALE_FACTOR
MARGIN = 10

# Global flags
ClampOutputFlag = False
LearningFlag = True
RandomInputFlag = True
homeostasisFlag = True
BlankInputFlag = False
printWeightFlag = False
quit_flag = False

# Simulation state
InputUnitOne = 0.5
InputUnitTwo = 0.5
RandCountDown = 0
learningCountdown = 0
normalizeFlag = 0
popWeight = 2.0

# Neural arrays
Ui = np.zeros(NUM_NEURONS)
Vi = np.zeros(NUM_NEURONS)
Yi = np.zeros(NUM_NEURONS)
OMi = np.full(NUM_NEURONS, 0.65)
THij = np.random.rand(NUM_NEURONS) * 0.5
Wij = np.random.rand(NUM_NEURONS, NUM_NEURONS)
Nij = np.random.choice([0, 1], size=(NUM_NEURONS, NUM_NEURONS))
Vis_Ui = np.zeros(NUM_NEURONS)
Neur_Ui = np.zeros(NUM_NEURONS)
VisWij = Wij.copy()

# Visual buffers
img_buffers = {
    "UnitOne": np.zeros((3*S_F, 3*S_F, 3), dtype=np.uint8),
    "UnitTwo": np.zeros((3*S_F, 3*S_F, 3), dtype=np.uint8),
    "UnitThree": np.zeros((3*S_F, 3*S_F, 3), dtype=np.uint8),
    "GaussOne": np.zeros((4*S_F, INPUT_LAYER*S_F, 3), dtype=np.uint8),
    "GaussTwo": np.zeros((4*S_F, INPUT_LAYER*S_F, 3), dtype=np.uint8),
    "GaussThree": np.zeros((4*S_F, INPUT_LAYER*S_F, 3), dtype=np.uint8),
    "PopOne": np.zeros((INPUT_LAYER*S_F, INPUT_LAYER*S_F, 3), dtype=np.uint8),
    "WeightOne": np.zeros((INPUT_LAYER*S_F, INPUT_LAYER*S_F, 3), dtype=np.uint8),
}

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def draw_neuron_circle(img, value, center, radius):
    val = value * 4
    r = 255 if val >= 3 else int((val - 2) * 255) if val >= 2 else 0
    g = int(255 * min(1, 4 - abs(val - 2))) if val < 4 else 0
    b = 255 if val <= 1 else int((2 - val) * 255) if val < 2 else 0
    cv2.circle(img, center, int(radius), (b, g, r), -1)

def neu_thread():
    global learningCountdown, normalizeFlag, popWeight, quit_flag
    while not quit_flag:
        Ui[0] = Vis_Ui[0]
        Ui[53] = Vis_Ui[53]

        Vi[:] = np.sum(Ui * Wij * (Nij == 1), axis=1)
        Yi[:] = sigmoid((THij - Vi) * 0.98)

        if ClampOutputFlag:
            OMi[275] = np.clip(2 * Yi[275] - Vis_Ui[275], 0, 1)

        if LearningFlag:
            learningCountdown += 1
            if learningCountdown > 30:
                i_post = 275
                for j_pre in range(106, 275):
                    if Nij[i_post][j_pre] == 1:
                        thetaY = Vis_Ui[275] - Yi[275]
                        deltaW = thetaY * Ui[j_pre] * 0.02
                        deltaW -= 0.0 * Wij[i_post][j_pre]
                        Wij[i_post][j_pre] = max(0, Wij[i_post][j_pre] + deltaW)
                learningCountdown = 0
                normalizeFlag = 1

        if homeostasisFlag and learningCountdown > 9:
            avg_activation = np.sum(Yi[106:275])
            thetaY = 15.0 - avg_activation
            deltaW = thetaY * 0.01
            popWeight += deltaW
            for i_post in range(106, 275):
                for j_pre in list(range(80, 106)) + list(range(27, 53)):
                    if Nij[i_post][j_pre] == 1:
                        Wij[i_post][j_pre] = popWeight
            learningCountdown = 0

        Ui[:] = Yi * 0.9 + Ui * 0.1

        if BlankInputFlag:
            Ui.fill(0)
            Yi.fill(0)

        Neur_Ui[:] = Ui
        VisWij[:] = Wij
        time.sleep(0.01)

def vis_thread():
    global InputUnitOne, InputUnitTwo, RandCountDown, BlankInputFlag, quit_flag
    for name in img_buffers:
        cv2.namedWindow(name)

    while not quit_flag:
        time.sleep(0.01)
        if RandomInputFlag:
            RandCountDown += 1
        if RandCountDown > 3:
            InputUnitOne = np.random.rand() * 0.35 + 0.4
            InputUnitTwo = np.random.rand() * 0.35 + 0.4
            RandCountDown = 0
            BlankInputFlag = True

        Vis_Ui[0] = InputUnitOne
        Vis_Ui[4 * INPUT_LAYER + 1] = InputUnitTwo
        idx = (4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)
        if ClampOutputFlag:
            Vis_Ui[idx] = (InputUnitOne + InputUnitTwo) / 2

        # Clear all
        for img in img_buffers.values():
            img[:] = 0

        draw_neuron_circle(img_buffers["UnitOne"], Vis_Ui[0], (int(1.5*S_F), int(1.5*S_F)), int(1.2*S_F))
        draw_neuron_circle(img_buffers["UnitTwo"], Vis_Ui[4 * INPUT_LAYER + 1], (int(1.5*S_F), int(1.5*S_F)), int(1.2*S_F))
        draw_neuron_circle(img_buffers["UnitThree"], Vis_Ui[idx], (int(1.5*S_F), int(1.5*S_F)), int(1.2*S_F))

        # Render Gauss and Pop layers (example shown only for GaussOne)
        for vi in range(4 * INPUT_LAYER):
            y, x = divmod(vi, INPUT_LAYER)
            center = (x * S_F + S_F // 2, y * S_F + S_F // 2)
            offset = 1
            draw_neuron_circle(img_buffers["GaussOne"], Vis_Ui[vi + offset], center, int(0.83 * S_F / 2))

        # Show images
        for name, img in img_buffers.items():
            cv2.imshow(name, img)

        key = cv2.waitKey(100) & 0xFF
        if key == 27:  # ESC
            quit_flag = True
        elif key in (ord('w'), ord('W')):
            printWeightFlag = True
        elif key in (ord('c'), ord('C')):
            #global ClampOutputFlag
            ClampOutputFlag = not ClampOutputFlag
        elif key in (ord('r'), ord('R')):
            #global RandomInputFlag
            RandomInputFlag = not RandomInputFlag
        elif key in (ord('l'), ord('L')):
            #global LearningFlag
            LearningFlag = not LearningFlag
        elif key in (ord('h'), ord('H')):
            #global homeostasisFlag
            homeostasisFlag = not homeostasisFlag

# Launch threads
threading.Thread(target=neu_thread, daemon=True).start()
vis_thread()
