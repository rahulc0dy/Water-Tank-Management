import pandas as pd
import numpy as np
import datetime
import random
import os

# --- Simulation Parameters ---
TANK_CAPACITY_LITRES = 1000.0
PUMP_ON_THRESHOLD = 10.0  # Pump turns ON when water level is at or below this percentage
PUMP_OFF_THRESHOLD = 95.0  # Pump turns OFF when water level is at or above this percentage
PUMP_FILL_RATE_PERCENT_PER_TICK = 4.0  # How much the pump fills in one 15-min interval

LEAK_DETECTION_START_HOUR = 2
LEAK_DETECTION_END_HOUR = 4

START_DATE = datetime.datetime(2025, 10, 1)
TIME_INTERVAL_MINUTES = 15

# --- Anomaly Probabilities ---
LEAK_NIGHT_PROBABILITY = 0.15  # 15% chance any given night has a leak
USAGE_PEAK_PROBABILITY = 0.01  # 1% chance of a sudden usage peak at any time
SENSOR_GLITCH_PROBABILITY = 0.005  # 0.5% chance of a random sensor glitch
SENSOR_STUCK_PROBABILITY = 0.001  # 0.1% chance the sensor gets stuck
EXTERNAL_FILL_PROBABILITY = 0.0005  # Very rare event for external tanker fill


def get_water_usage(hour, is_weekend):
    """Simulates more realistic water usage based on the time of day and day of the week."""

    # --- Night Time: Very low to zero usage ---
    if 0 <= hour <= 5:
        # Most of the time, there is zero usage at night.
        # Add a small chance for a quick, small usage event (e.g., toilet flush).
        if random.random() < 0.05:  # 5% chance of a small usage event
            return np.random.uniform(0.5, 1.0)
        else:
            return 0.0  # Absolutely no usage

    # --- Day Time ---
    if is_weekend:
        # Weekend: Usage starts later and is more spread out
        if 8 <= hour <= 11:  # Morning activity
            base_usage = np.random.uniform(0.8, 2.5)
        elif 12 <= hour <= 20:  # Consistent daytime/evening usage
            base_usage = np.random.uniform(0.6, 2.2)
        elif 21 <= hour <= 23:  # Tapering off
            base_usage = np.random.uniform(0.2, 1.0)
        else:  # Early morning before activity starts (6-7 AM)
            base_usage = np.random.uniform(0.1, 0.5)
    else:
        # Weekday: Distinct morning and evening peaks
        if 6 <= hour <= 9:  # Morning rush
            base_usage = np.random.uniform(1.5, 4.0)
        elif 10 <= hour <= 17:  # Lower daytime usage (work/school hours)
            base_usage = np.random.uniform(0.3, 1.2)
        elif 18 <= hour <= 22:  # Evening peak (cooking, cleaning)
            base_usage = np.random.uniform(1.2, 3.5)
        else:  # Late evening
            base_usage = np.random.uniform(0.1, 0.5)

    return base_usage * np.random.uniform(0.8, 1.2)  # Add some natural randomness


def generate_dataset(simulation_duration_days):
    """Generates the entire dataset with anomalies for a given duration."""

    time_now = START_DATE
    end_time = START_DATE + datetime.timedelta(days=simulation_duration_days)

    data = []

    # Initialize state
    water_level = 85.0  # Start with a reasonably full tank
    pump_state = 0  # Pump is initially off
    is_leaking_tonight = False
    sensor_stuck_at = None
    sensor_stuck_counter = 0

    print(f"Generating dataset for {simulation_duration_days} days...")

    while time_now < end_time:
        # Check if it's a new day to decide if a leak should happen tonight
        if time_now.hour == 0 and time_now.minute == 0:
            is_leaking_tonight = random.random() < LEAK_NIGHT_PROBABILITY
            if is_leaking_tonight:
                print(f"INFO: Simulating a leak for the night of {time_now.date()}")

        # --- Determine Targets for the CURRENT state ---

        # Target 1: Pump Signal Logic (Hysteresis)
        if water_level <= PUMP_ON_THRESHOLD:
            pump_signal_target = 1
        elif water_level >= PUMP_OFF_THRESHOLD:
            pump_signal_target = 0
        else:
            # If in the middle range, keep the current state
            pump_signal_target = pump_state

        # Target 2: Leak Detection Activation Logic
        is_leak_window = LEAK_DETECTION_START_HOUR <= time_now.hour < LEAK_DETECTION_END_HOUR
        leak_detection_target = 1 if is_leak_window else 0

        # --- Record Current State ---

        current_record = {
            'timestamp': time_now.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
            'water_level_percent': round(water_level, 2),
            'pump_state': pump_state,
            'water_volume_litres': round(water_level / 100 * TANK_CAPACITY_LITRES, 0),
            'pump_signal_target': pump_signal_target,
            'leak_detection_active_target': leak_detection_target
        }
        data.append(current_record)

        # --- Update State for the NEXT Interval ---

        # 1. Apply pump action
        if pump_state == 1:
            water_level += PUMP_FILL_RATE_PERCENT_PER_TICK

        # 2. Apply normal usage
        is_weekend = time_now.weekday() >= 5  # Saturday or Sunday
        usage = get_water_usage(time_now.hour, is_weekend)
        water_level -= usage

        # 3. Apply leak if active
        if is_leak_window and is_leaking_tonight:
            water_level -= np.random.uniform(0.1, 0.3)  # Slow, consistent drop

        # 4. Inject Anomalies

        # Sudden Usage Peak
        if random.random() < USAGE_PEAK_PROBABILITY:
            water_level -= np.random.uniform(10, 20)
            print(f"ANOMALY: Sudden usage peak at {time_now}")

        # Sensor Glitch
        if random.random() < SENSOR_GLITCH_PROBABILITY:
            glitch_value = np.random.uniform(0, 100)
            glitch_record = current_record.copy()
            glitch_record['water_level_percent'] = round(glitch_value, 2)
            data[-1] = glitch_record
            print(f"ANOMALY: Sensor glitch at {time_now}, reading: {glitch_value:.2f}%")

        # Stuck Sensor
        if sensor_stuck_at is not None:
            data[-1]['water_level_percent'] = sensor_stuck_at
            sensor_stuck_counter -= 1
            if sensor_stuck_counter <= 0:
                sensor_stuck_at = None
                print(f"INFO: Sensor unstuck at {time_now}")
        elif random.random() < SENSOR_STUCK_PROBABILITY:
            sensor_stuck_at = round(water_level, 2)
            sensor_stuck_counter = random.randint(5, 12)
            print(f"ANOMALY: Sensor stuck at {sensor_stuck_at}% starting at {time_now}")

        # External Fill Event
        if random.random() < EXTERNAL_FILL_PROBABILITY and pump_state == 0:
            fill_amount = np.random.uniform(30, 60)
            water_level += fill_amount
            print(f"ANOMALY: External fill event of {fill_amount:.2f}% at {time_now}")

        # 5. Ensure water level is within bounds
        water_level = max(0, min(100, water_level))

        # 6. Update the pump state for the next iteration based on the target we calculated
        pump_state = pump_signal_target

        # Move time forward
        time_now += datetime.timedelta(minutes=TIME_INTERVAL_MINUTES)

    print("Dataset generation complete.")
    return pd.DataFrame(data)


# --- Main Execution ---
if __name__ == "__main__":
    try:
        days_to_simulate = int(input("Enter the number of days to simulate: "))
        if days_to_simulate <= 0:
            print("Error: Please enter a positive number of days.")
            exit()
    except ValueError:
        print("Error: Invalid input. Please enter a whole number.")
        exit()

    generated_df = generate_dataset(days_to_simulate)

    # --- Save to CSV ---
    output_directory = "data"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        print(f"Created directory: '{output_directory}'")

    file_name_input = input("Enter the file name for the CSV (without extension): ")
    output_filename = file_name_input + ".csv"
    full_path = os.path.join(output_directory, output_filename)

    generated_df.to_csv(full_path, index=False)

    print(f"\nSuccessfully generated '{full_path}' with {len(generated_df)} rows.")
    print("Script finished. The CSV file is ready.")

