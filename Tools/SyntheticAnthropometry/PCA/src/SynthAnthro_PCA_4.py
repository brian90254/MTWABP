# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SyntheticAnthropometry/PCA
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/SynthAnthro_PCA_4.py
# COMMAND LINE WILL PROMPT YOU FOR A MEASUREMENT LIST FILE IN THE "CSV" DIRECORY
#   [0] == SynthAnthro_SizeAndShape_CSV_FEMALE_1.csv
#   [1] == SynthAnthro_SizeAndShape_CSV_MALE_1.csv
#
# ...or
#
# RUN THE "command" SCRIPT DIRECTLY, DOUBLE CLICK:
#   runSynthAnthro_PCA.command

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import sys
import os

# === CONFIGURATION ===
#delimiter = "\t"  # Use ',' if your CSV is comma-separated
delimiter = ","  # Use '\t' if your CSV is comma-separated

def prompt_for_measurement_file():
    base_dir = "CSV"
    files = [f for f in os.listdir(base_dir) if f.lower().endswith('.csv')]
    if not files:
        print(f"No CSV files found in {base_dir}")
        sys.exit(1)

    print(f"\nAvailable CSV files in '{base_dir}':")
    for i, f in enumerate(files):
        print(f"[{i}] {f}")
    
    while True:
        try:
            index = int(input("\nEnter the number of the measurement CSV file to use: ").strip())
            if 0 <= index < len(files):
                return os.path.join(base_dir, files[index])
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

# === Load your CSV file ===
#filename = "CSV/SynthAnthro_SizeAndShape_CSV_MALE_12.csv"  # <- Change to your actual filename
filename = prompt_for_measurement_file()
# === Output File Name ===
output_dir = "PCA_Loading_LeaveOneOut"

# === Load the dataset ===
df = pd.read_csv(filename, sep=delimiter)
num_rows, num_columns = df.shape
print(f"✅ Loaded data with {num_rows} rows and {num_columns} columns.")

# === Create output directory ===
os.makedirs(output_dir, exist_ok=True)

# === Sweep: leave-one-column-out ===
for exclude_col in df.columns:
    print(f"\n🔍 Excluding column: {exclude_col}")
    
    # Create reduced DataFrame without one column
    df_reduced = df.drop(columns=[exclude_col])
    
    # Standardize the reduced data
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df_reduced)
    
    # Apply PCA
    pca = PCA()
    pca.fit(scaled_data)
    
    # Get loadings
    loadings = pca.components_.T
    pca_columns = [f'PC{i+1}' for i in range(loadings.shape[1])]
    loadings_df = pd.DataFrame(loadings, index=df_reduced.columns, columns=pca_columns)
    
    # Save loadings to CSV
    clean_colname = exclude_col.replace("/", "_")  # clean up filenames
    output_path = os.path.join(output_dir, f"loadings_wo_{clean_colname}.csv")
    loadings_df.to_csv(output_path)

    print(f"✅ Saved loadings (without '{exclude_col}') to {output_path}")
