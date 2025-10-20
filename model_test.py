import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

MODEL_FILE = Path('model') / 'aqua_man_model.pkl'
SCALER_FILE = Path('model') / 'aqua_man_scaler.pkl'


def main():
    # Load model
    try:
        model = joblib.load(MODEL_FILE)
    except FileNotFoundError:
        print(f"Error: Model file '{MODEL_FILE.as_posix()}' not found.")
        sys.exit(1)

    # Load scaler if present (optional)
    scaler = None
    try:
        scaler = joblib.load(SCALER_FILE)
    except FileNotFoundError:
        pass

    # Use the training input columns only (keep it simple)
    feature_names = ['timestamp', 'water_level_percent', 'pump_state', 'water_volume_litres']

    # Create a small random DataFrame (20 rows)
    rng = np.random.RandomState(42)
    n_rows = 20
    X = pd.DataFrame({f: rng.rand(n_rows) for f in feature_names})

    # Generate a simple timestamp range (15-minute steps ending now UTC)
    ts = pd.date_range(end=pd.Timestamp.utcnow(), periods=n_rows, freq='15min')
    # Use numeric epoch seconds if 'timestamp' is a feature
    epoch_seconds = (ts.astype('int64') // 10**9).astype(float)

    # If the model directly expects a numeric 'timestamp' or '*epoch*' feature
    if 'timestamp' in feature_names:
        X['timestamp'] = epoch_seconds.values
    for f in feature_names:
        if 'epoch' in f.lower() and f != 'timestamp':
            X[f] = epoch_seconds.values

    # Use realistic ranges for known features
    if 'water_level_percent' in feature_names:
        X['water_level_percent'] = rng.uniform(0.0, 100.0, n_rows)
    if 'water_volume_litres' in feature_names:
        X['water_volume_litres'] = rng.uniform(0.0, 1000.0, n_rows)

    # Keep binary-like columns as 0/1 when named like 'state' or 'signal'
    for f in feature_names:
        fl = f.lower()
        if fl.endswith(('state', 'signal')):
            X[f] = (rng.rand(n_rows) > 0.5).astype(int)

    # Prepare input matrix to match model/scaler expectations (keep it simple)
    X_use = X
    expected_n = getattr(model, 'n_features_in_', X.shape[1])
    scaler_used = False

    if scaler is not None and hasattr(scaler, 'feature_names_in_'):
        scaler_features = list(scaler.feature_names_in_)
        if all(f in X.columns for f in scaler_features):
            X_use = X[scaler_features]
        else:
            X_use = X
        try:
            X_in = scaler.transform(X_use)
            scaler_used = True
        except Exception as e:
            print(f"Warning: Failed to apply scaler, proceeding with raw values. Reason: {e}")
            # Fallback to raw values
            X_in = X_use.values
            scaler_used = False
    else:
        # No scaler or no feature names: use a minimal subset if needed
        if expected_n == X.shape[1]:
            X_in = X.values
        elif expected_n == 1 and 'water_level_percent' in X.columns:
            X_in = X[['water_level_percent']].values
        else:
            X_in = X.iloc[:, :expected_n].values
        scaler_used = False

    # Diagnostics before prediction
    print('features:', feature_names)
    print(f"model: {type(model).__name__}, n_features_in_: {expected_n}")
    if hasattr(model, 'classes_'):
        print('model classes_:', getattr(model, 'classes_', None))
    print(f"scaler_used: {scaler_used}")
    if scaler_used and hasattr(scaler, 'feature_names_in_'):
        print('scaler feature order:', list(scaler.feature_names_in_))
    print('X_use feature ranges (min..max) before scaling:')
    try:
        for col in X_use.columns:
            col_min = float(np.nanmin(X_use[col]))
            col_max = float(np.nanmax(X_use[col]))
            print(f"  {col}: {col_min:.3g} .. {col_max:.3g}")
    except Exception:
        pass
    print('X sample:')
    print(X.head())

    # Predict
    preds = model.predict(X_in)

    print('predictions (first 10):', preds[:10])
    try:
        vals, counts = np.unique(preds, return_counts=True)
        print('prediction distribution:', dict(zip(vals.tolist(), counts.tolist())))
    except Exception:
        pass

    # Optional: show class balance in available training CSVs for common targets
    training_files = [
        Path('data') / 'training_dataset_01.csv',
        Path('data') / 'training_dataset_02.csv',
        Path('data') / 'training_dataset_03.csv',
    ]
    printed_balance = False
    for tf in training_files:
        if tf.exists():
            try:
                df_train = pd.read_csv(tf)
                for target_col in ['leak_detection_active_target', 'pump_signal_target']:
                    if target_col in df_train.columns:
                        vc = df_train[target_col].value_counts().to_dict()
                        print(f"{tf.name} target balance for {target_col}: {vc}")
                        printed_balance = True
            except Exception:
                continue
    if not printed_balance:
        print('Note: Could not infer training target balance (no training CSVs found or readable).')


if __name__ == '__main__':
    main()