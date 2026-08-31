import csv
import random

OUTPUT_FILE = "fire_timeseries.csv"
SAMPLES = 10000   # good for training

def spread_label(wind, severity, humidity):
    """
    Rule-based ground truth (acts as teacher for LSTM)
    """
    if severity == 3 and wind > 12 and humidity < 40:
        return 2  # HIGH
    if severity >= 2 and wind > 8:
        return 1  # MEDIUM
    return 0      # LOW

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["wind", "dir", "severity", "humidity", "spread"])

    for _ in range(SAMPLES):
        wind = round(random.uniform(2, 20), 2)
        direction = random.randint(0, 360)
        severity = random.choice([1, 2, 3])
        humidity = random.randint(20, 90)

        spread = spread_label(wind, severity, humidity)

        writer.writerow([wind, direction, severity, humidity, spread])

print("✅ fire_timeseries.csv created successfully")
