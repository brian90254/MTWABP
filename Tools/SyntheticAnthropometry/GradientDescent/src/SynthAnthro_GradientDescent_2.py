# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SyntheticAnthropometry/GradientDescent
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/SynthAnthro_GradientDescent_1.py
#


import pandas as pd
import numpy as np

# --- CONFIGURATION ---
# model_csv = 'models.csv'         # Path to the CSV with the 10 standard models
# target_csv = 'target.csv'        # Path to the target CSV file
model_csv = 'CSV/measurementResults_BLENDED_MALE.csv'         # Path to the CSV with the 10 standard models
target_csv = 'CSV/measurementTarget_Test_1.csv'        # Path to the target CSV file
learning_rate = 0.01
#max_iterations = 10000
max_iterations = 1000000
#tolerance = 1e-8
tolerance = 1e-10

# --- LOAD MODEL DATA ---
df_models = pd.read_csv(model_csv)
model_names = df_models['File'].values
data = df_models.drop(columns='File').values  # shape: (num_models, num_features)
num_models, num_features = data.shape

# Transpose so columns are per model, rows per feature
data_T = data.T  # shape: (num_features, num_models)

# --- LOAD TARGET VECTOR ---
df_target = pd.read_csv(target_csv)
if df_target.shape[0] != 1:
    raise ValueError("Target CSV must contain exactly one row of data.")
target = df_target.drop(columns='File').values.flatten()

if len(target) != num_features:
    raise ValueError("Target vector must have the same number of features as the model data.")

# --- INITIALIZE WEIGHTS ---
weights = np.random.uniform(-0.1, 0.1, num_models)
weights /= np.sum(weights)  # normalize

# --- GRADIENT DESCENT LOOP ---
errors = []
for iteration in range(max_iterations):
    #print("\nLooping")
    prediction = data_T @ weights
    error_vector = prediction - target
    rms_error = np.sqrt(np.mean(error_vector ** 2))
    errors.append(rms_error)

    # Compute gradient
    #gradient = 2 * (data_T @ error_vector) / num_features
    gradient = 2 * (data @ error_vector) / num_features

    # Update weights
    weights -= learning_rate * gradient
    #weights /= np.sum(weights)  # re-normalize

    # Check convergence
    if iteration > 0 and abs(errors[-2] - rms_error) < tolerance:
        print(f"Converged at iteration {iteration}")
        break

# --- RESULTS ---
print("\nFinal RMS Error:", errors[-1])
print("\nOptimized Weights:")
for name, w in zip(model_names, weights):
    print(f"{name}: {w:.4f}")

# Save weights to CSV
output_df = pd.DataFrame({'File': model_names, 'Weight': weights})
output_df.to_csv('optimized_weights.csv', index=False)
