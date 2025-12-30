import sys
import os
import time
import argparse
from datetime import datetime
from pathlib import Path

import serial
import joblib
import numpy as np
import pandas as pd

from backend.database import get_db
from backend.models import Telemetry

MODEL_FILE = Path('model') / 'aqua_man_model.pkl'
SCALER_FILE = Path('model') / 'aqua_man_scaler.pkl'


def load_model_and_scaler():
    try:
        mdl = joblib.load(MODEL_FILE)
    except FileNotFoundError:
        print(f"Error: Model file '{MODEL_FILE.as_posix()}' not found.")
        sys.exit(1)

    try:
        scl = joblib.load(SCALER_FILE)
    except FileNotFoundError:
        scl = None
    return mdl, scl


def open_serial(port: str, baud: int, timeout: float = 1.0) -> serial.Serial:
    try:
        ser = serial.Serial(port=port, baudrate=baud, timeout=timeout)
        time.sleep(2)  # allow Arduino to reset
        print(f"Connected to Arduino on {port} @ {baud} baud.")
        return ser
    except serial.SerialException as e:
        print(f"Error: Could not connect to Arduino on port '{port}'. {e}")
        sys.exit(2)


def build_feature_row(level_percent: float, pump_state: int) -> pd.DataFrame:
    # Epoch seconds as float
    epoch_secs = float(time.time())
    # If volume is a required feature, derive a naive estimate from level (assume 1000L tank if unknown)
    est_volume_l = level_percent / 100.0 * 1000.0
    row = {
        'timestamp': epoch_secs,
        'water_level_percent': float(level_percent),
        'pump_state': int(pump_state),
        'water_volume_litres': float(est_volume_l),
    }
    return pd.DataFrame([row])


def prepare_X(df_row: pd.DataFrame, model, scaler):
    X_use = df_row
    # Prefer scaler feature order if available
    if scaler is not None and hasattr(scaler, 'feature_names_in_'):
        feat_order = list(scaler.feature_names_in_)
        missing = [f for f in feat_order if f not in df_row.columns]
        if missing:
            # For any missing features, create zeros
            for f in missing:
                X_use[f] = 0.0
        X_use = X_use[feat_order]
        try:
            X_in = scaler.transform(X_use)
            return X_in
        except Exception as e:
            print(f"Warning: Failed to apply scaler, using raw features. Reason: {e}")
            return X_use.values
    # Otherwise match model expected number of features
    expected_n = getattr(model, 'n_features_in_', X_use.shape[1])
    if expected_n == X_use.shape[1]:
        return X_use.values
    # Heuristics to select subset
    cols_priority = [
        'timestamp', 'water_level_percent', 'pump_state', 'water_volume_litres'
    ]
    cols = [c for c in cols_priority if c in X_use.columns]
    if len(cols) >= expected_n:
        return X_use[cols[:expected_n]].values
    # pad with zeros if model expects more
    arr = X_use[cols].values
    if arr.shape[1] < expected_n:
        pad = np.zeros((arr.shape[0], expected_n - arr.shape[1]))
        arr = np.concatenate([arr, pad], axis=1)
    return arr


def predict_command(model, X_in) -> str:
    cmd_bool = None
    try:
        # Classification with probabilities
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(X_in)
            # If binary, positive class probability is proba[:, 1]
            if proba.shape[1] == 2:
                cmd_bool = (proba[:, 1] >= 0.5)[0]
            else:
                # Multiclass: choose class 1 if it exists else argmax == 1
                classes = getattr(model, 'classes_', None)
                if classes is not None and 1 in list(classes):
                    idx = list(classes).index(1)
                    cmd_bool = (proba.argmax(axis=1) == idx)[0]
                else:
                    cmd_bool = (proba.argmax(axis=1)[0] == 1)
        else:
            pred = model.predict(X_in)[0]
            if isinstance(pred, (np.bool_, bool)):
                cmd_bool = bool(pred)
            elif isinstance(pred, (np.integer, int, np.floating, float)):
                # Treat numeric predictions >= 0.5 as ON
                cmd_bool = float(pred) >= 0.5
            else:
                # Fallback: try to cast
                try:
                    cmd_bool = float(pred) >= 0.5
                except Exception:
                    cmd_bool = False
    except Exception as e:
        print(f"Warning: Prediction failed, defaulting to OFF. Reason: {e}")
        cmd_bool = False
    return '1' if cmd_bool else '0'


def parse_arduino_line(line: str):
    # Expected format: "level_percent,pump_state"
    parts = [p.strip() for p in line.split(',') if p.strip() != '']
    if len(parts) < 2:
        raise ValueError(f"Malformed line (expected 'level,pump'): '{line}'")
    level = float(parts[0])
    pump_state = int(float(parts[1]))
    return level, pump_state

def no_model_command(
    current_level: float,
    current_pump_state: int,
    previous_command = None,
) -> str:
    if current_level <= 6.0:
        return "1"
    if current_level >= 99.0:
        return "0"
    if previous_command is not None:
        return previous_command
    return "1" if current_pump_state else "0"

def main():
    parser = argparse.ArgumentParser(description='AquaMan automation: model-driven pump control over Arduino serial')
    parser.add_argument('--port', default=os.environ.get('AQUA_SERIAL_PORT', '/dev/ttyUSB0'), help='Serial port (e.g., COM3 or /dev/ttyACM0)')
    parser.add_argument('--baud', default=int(os.environ.get('AQUA_SERIAL_BAUD', '9600')), type=int, help='Baud rate (default 9600)')
    parser.add_argument('--interval', default=0.1, type=float, help='Loop sleep interval in seconds')
    parser.add_argument('--dry-run', action='store_true', help='Do not send commands to Arduino, only print decisions')
    parser.add_argument('--no-model', action='store_true', help='Use simple control; skip ML model')
    args = parser.parse_args()

    if args.no_model:
        print("Running in NM mode: Thresholds (6%, 99%)")
    else:
        model, scaler = load_model_and_scaler()

    # Initialize database session
    db_gen = get_db()
    db = next(db_gen)
    ser = open_serial(args.port, args.baud, timeout=1.0)
    last_command = None

    print('Beginning operation. Press Ctrl+C to exit.')
    try:
        while True:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        time.sleep(args.interval)
                        continue
                    try:
                        level, pump_state = parse_arduino_line(line)
                    except Exception as pe:
                        print(f"Skip malformed line: {line} ({pe})")
                        continue

                    df_row = build_feature_row(level, pump_state)
                    if args.no_model:
                        cmd = no_model_command(level, pump_state, last_command)
                    else:
                        X_in = prepare_X(df_row, model, scaler)
                        cmd = predict_command(model, X_in)
                    last_command = cmd

                    if not args.dry_run:
                        try:
                            ser.write(cmd.encode('utf-8'))
                        except Exception as we:
                            print(f"Warning: Failed to write to serial: {we}")
                    try:
                        telemetry_entry = Telemetry(
                            timestamp=datetime.utcnow(),
                            water_level_percent=level,
                            pump_state=pump_state
                        )
                        db.add(telemetry_entry)
                        db.commit()
                    except Exception as store_exc:
                        print(f"Warning: Failed to persist telemetry: {store_exc}")
                        db.rollback()
                    now = time.strftime('%H:%M:%S')
                    print(f"{now} level%: {level:.2f}, pump_state: {pump_state}, cmd: {cmd}")
                else:
                    time.sleep(args.interval)
            except Exception as e:
                print(f"An error occurred in loop: {e}")
                time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        print('\nExiting program.')
    finally:
        try:
            ser.close()
        except Exception:
            pass
        try:
            # Close the database generator to trigger cleanup
            next(db_gen)
        except StopIteration:
            pass
        except Exception:
            pass


if __name__ == '__main__':
    main()