import numpy as np
import time

# Constants and configuration
NUM_NEURONS = 328
LEARNING_RATE = 0.02
DECAY_EPSILON = 0.0
THRESHOLD_VALUE = 0.65
HOMEOSTASIS_LEARNING_RATE = 0.01

# Neural simulation variables
Ui = np.zeros(NUM_NEURONS)   # Input activation
Vi = np.zeros(NUM_NEURONS)   # Weighted sum of inputs
Yi = np.zeros(NUM_NEURONS)   # Neuron activation output
OMi = np.full(NUM_NEURONS, THRESHOLD_VALUE)  # Adaptive threshold or memory

Wij = np.random.rand(NUM_NEURONS, NUM_NEURONS)  # Synaptic weights
Nij = np.random.choice([0, 1], size=(NUM_NEURONS, NUM_NEURONS))  # Connectivity matrix
THij = np.random.rand(NUM_NEURONS) * 0.5  # Thresholds for each neuron

Vis_Ui = np.zeros(NUM_NEURONS)
Neur_Ui = np.zeros(NUM_NEURONS)
VisWij = np.zeros((NUM_NEURONS, NUM_NEURONS))

# Simulation control flags and variables
ClampOutputFlag = 0
LearningFlag = 1
homeostasisFlag = 1
BlankInputFlag = 0
printWeightFlag = 0
quit_flag = False
learningCountdown = 0
normalizeFlag = 0
popWeight = 2.0

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def neu_thread():
    global Ui, Vi, Yi, OMi, Wij, Nij, THij
    global Vis_Ui, Neur_Ui, VisWij
    global ClampOutputFlag, LearningFlag, homeostasisFlag
    global BlankInputFlag, printWeightFlag, quit_flag
    global learningCountdown, normalizeFlag, popWeight

    print("Hello, World! From NEU Thread!!!")
    time.sleep(0.1)

    while not quit_flag:
        # Set some specific input neurons from visual input
        Ui[0] = Vis_Ui[0]
        Ui[53] = Vis_Ui[53]

        # Weighted input: Vi = sum(Uj * Wij * Nij condition)
        for ni in range(NUM_NEURONS):
            Vi[ni] = np.sum(Ui * Wij[ni] * ((Nij[ni] == 1) | (Nij[ni] == -1)))

        # Apply activation function with bias from THij
        Yi = sigmoid((THij - Vi) * 0.98)

        # Supervised learning: clamp output neuron if flag is set
        if ClampOutputFlag:
            OMi[275] = max(0, min(1, 2 * Yi[275] - Vis_Ui[275]))

        # Learning rule: cerebellar plasticity
        if LearningFlag:
            learningCountdown += 1
            if learningCountdown > 30:
                i_post = 275
                for j_pre in range(106, 275):
                    if Nij[i_post][j_pre] == 1:
                        thetaY = Vis_Ui[275] - Yi[275]
                        deltaW = thetaY * Ui[j_pre] * LEARNING_RATE
                        deltaW -= DECAY_EPSILON * Wij[i_post][j_pre]
                        Wij[i_post][j_pre] = max(0, Wij[i_post][j_pre] + deltaW)
                learningCountdown = 0
                normalizeFlag = 1

        # Homeostatic plasticity: keep overall output activation in balance
        if homeostasisFlag:
            learningCountdown += 1
            if learningCountdown > 9:
                avg_activation = np.sum(Yi[106:275])
                thetaY = 15.0 - avg_activation
                deltaW = thetaY * HOMEOSTASIS_LEARNING_RATE
                popWeight += deltaW
                for i_post in range(106, 275):
                    for j_pre in list(range(80, 106)) + list(range(27, 53)):
                        if Nij[i_post][j_pre] == 1:
                            Wij[i_post][j_pre] = popWeight
                learningCountdown = 0

        # Update input with persistence (leaky integration)
        Ui = Yi * 0.9 + Ui * 0.1

        # If blanking is flagged, reset all neurons
        if BlankInputFlag:
            Ui.fill(0)
            Yi.fill(0)
            BlankInputFlag = 0

        # Update visualization arrays
        Neur_Ui[:] = Ui
        VisWij[:] = Wij

        if printWeightFlag:
            for i_post in range(106, 275):
                print(f"Neuron {i_post} weights:")
                print(Wij[i_post, 250:275])
            printWeightFlag = 0

        time.sleep(0.01)  # mimic short delay
