# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SyntheticAnthropometry/CAESAR
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/SynthAnthro_PCA_2.py

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import sys

# === CONFIGURATION ===
#filename = "your_data.csv"  # <-- Replace with your actual filename
#delimiter = "\t"  # Use ',' if your CSV is comma-separated
delimiter = ","  # Use '\t' if your CSV is comma-separated

# === Load your CSV file ===
#filename = "your_data.csv"  # <- Change to your actual filename
filename = "CSV/SynthAnthro_SizeAndShape_CSV_FEMALE_1.csv"  # <- Change to your actual filename
#filename = "CSV/SynthAnthro_ShapeOnly_CSV_MALE_5.csv"  # <- Change to your actual filename


#df = pd.read_csv(filename, sep="\t")  # Use sep="," if it's comma-separated
#df = pd.read_csv(filename, sep=",")  # Use sep="\t" if it's tab-separated

# === Load the CSV file ===
try:
    df = pd.read_csv(filename, sep=delimiter)
except Exception as e:
    print(f"Error loading file: {e}")
    sys.exit(1)

# === Detect and report size ===
num_rows, num_columns = df.shape
print(f"\n✅ Loaded CSV with {num_rows} rows and {num_columns} columns.")

# === Warning: Not enough features for PCA ===
if num_columns < 2:
    print("❌ Not enough features for PCA. At least 2 columns are required.")
    sys.exit(1)

# === Standardize the data ===
scaler = StandardScaler()
scaled_data = scaler.fit_transform(df)

# === Apply PCA ===
pca = PCA()
principal_components = pca.fit_transform(scaled_data)

# === Build DataFrame for output ===
pca_columns = [f'PC{i+1}' for i in range(principal_components.shape[1])]
pca_df = pd.DataFrame(principal_components, columns=pca_columns)

# === Report explained variance ===
print("\n📊 Explained Variance Ratio:")
for i, var in enumerate(pca.explained_variance_ratio_):
    print(f"  PC{i+1}: {var:.3f}")

# === Plot the first 2 principal components ===
plt.figure(figsize=(8, 6))
plt.scatter(pca_df['PC1'], pca_df['PC2'], c='blue', edgecolor='k', alpha=0.7)
plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)")
plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)")
plt.title("PCA: First Two Principal Components")
plt.grid(True)
plt.tight_layout()
plt.show()

#pca_df.to_csv("pca_output.csv", index=False)

# === Identify feature names and component loadings ===
feature_names = df.columns
loadings = pca.components_.T

loadings_df = pd.DataFrame(loadings, index=feature_names, columns=pca_columns)

print("\n🔍 PCA Loadings (Feature contributions to each Principal Component):")
print(loadings_df.round(3))

# Optional: Save to CSV
loadings_df.to_csv("pca_loadings.csv")
