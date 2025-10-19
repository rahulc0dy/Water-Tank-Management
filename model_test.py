import sys
import joblib
import pandas as pd

# Define `data` as a DataFrame with a single column `ambience_lux` containing 50 different values
data = pd.DataFrame({
    "ambience_lux": [float(i) for i in range(50)]
})

# Quick verification prints
print(data.head())
print("data shape:", data.shape)

try:
    model = joblib.load('model/aqua_man.pkl')
except FileNotFoundError:
    print("Error: Model file 'aqua_man.pkl' not found.")
    exit()

print(model.predict(data))