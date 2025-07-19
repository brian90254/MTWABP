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
#   python src/SynthAnthro_PCA_1.py

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# === Load your CSV file ===
#filename = "your_data.csv"  # <- Change to your actual filename
filename = "CSV/SynthAnthro_SizeAndShape_CSV_MALE_1.csv"  # <- Change to your actual filename

#df = pd.read_csv(filename, sep="\t")  # Use sep="," if it's comma-separated
df = pd.read_csv(filename, sep=",")  # Use sep="\t" if it's tab-separated

# === Optionally display the first few rows ===
print("Original Data:")
print(df.head())

# === Standardize the data ===
scaler = StandardScaler()
scaled_data = scaler.fit_transform(df)

# === Apply PCA ===
pca = PCA()
principal_components = pca.fit_transform(scaled_data)

# === Create a DataFrame with PCA results ===
pca_columns = [f'PC{i+1}' for i in range(principal_components.shape[1])]
pca_df = pd.DataFrame(data=principal_components, columns=pca_columns)

# === Show explained variance ===
explained_var = pca.explained_variance_ratio_
print("\nExplained Variance Ratio:")
for i, var in enumerate(explained_var):
    print(f'PC{i+1}: {var:.3f}')

# === Plot the first 2 principal components ===
plt.figure(figsize=(8, 6))
plt.scatter(pca_df['PC1'], pca_df['PC2'], c='blue', edgecolor='k')
plt.xlabel(f"PC1 ({explained_var[0]*100:.1f}% variance)")
plt.ylabel(f"PC2 ({explained_var[1]*100:.1f}% variance)")
plt.title("PCA: First Two Principal Components")
plt.grid(True)
plt.tight_layout()
plt.show()
