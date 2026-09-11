"""
Live-Heatmap-Visualisierung für die Druckmatrix (14 Zeilen x 16 Spalten).

Mit Kalibrierung: Baseline-Subtraktion (Nullmessung) + Schwellwert, damit nur
echter Druck ein Signal erzeugt und das bloße Aufeinanderliegen der Matten unterdrückt wird.

Bedienung (Tasten im Heatmap-Fenster):
    b : Baseline erfassen (Nullmessung).
    r : Baseline zurücksetzen (wieder Rohwerte anzeigen).
    + : Schwellwert erhöhen (unempfindlicher, weniger Rauschen).
    - : Schwellwert senken (empfindlicher).
    s : Aktuellen kalibrierten Frame als CSV speichern.
    x : Aktuellen ROHEN Frame als CSV speichern (für Analyse/Debug).
"""

import time
import numpy as np
import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Einstellungen ---
PORT = "COM5"       # Aktualisiert auf COM5
BAUD = 115200
ROWS, COLS = 14, 16

# --- Kalibrier-Parameter ---
THRESHOLD = 300
THRESHOLD_STEP = 50
BASELINE_FRAMES = 20
BASELINE_MARGIN = 50
DISPLAY_VMAX = 2000

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # ESP32 Reset nach dem Öffnen des seriellen Ports abwarten

raw_data = np.zeros((ROWS, COLS))
data = np.zeros((ROWS, COLS))
baseline = np.zeros((ROWS, COLS))
baseline_active = False

def read_frame():
    """Liest einen kompletten Frame zwischen START und END vom ESP32."""
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if line == "START":
            break
        if line == "":
            return None

    frame = []
    for _ in range(ROWS):
        line = ser.readline().decode(errors="ignore").strip()
        try:
            values = [int(v) for v in line.split(",")]
        except ValueError:
            return None
        if len(values) != COLS:
            return None
        frame.append(values)

    end_marker = ser.readline().decode(errors="ignore").strip()
    if end_marker != "END":
        return None

    return np.array(frame)

def calibrate(frame):
    if baseline_active:
        signal = frame.astype(float) - baseline
    else:
        signal = frame.astype(float)
    signal = np.clip(signal, 0, None)
    signal[signal < THRESHOLD] = 0
    return signal

def capture_baseline():
    global baseline, baseline_active
    frames = []
    print(f"Erfasse Baseline über {BASELINE_FRAMES} Frames ... "
          f"(jetzt KEIN Fuß/Gewicht auflegen)")
    while len(frames) < BASELINE_FRAMES:
        f = read_frame()
        if f is not None:
            frames.append(f.astype(float))
    baseline = np.mean(frames, axis=0) + BASELINE_MARGIN
    baseline_active = True
    print("Baseline gesetzt. Fuß mit Gewicht kann jetzt aufgesetzt werden.")

fig, ax = plt.subplots(figsize=(8, 5))
im = ax.imshow(data, cmap="inferno", vmin=0, vmax=DISPLAY_VMAX, aspect="auto")
cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Druck-Signal (ADC nach Kalibrierung)")

def update_title():
    ax.set_title(
        f"Druckverteilung | Schwelle={THRESHOLD} | "
        f"Baseline={'AN' if baseline_active else 'AUS'}  "
        f"(b=Baseline, +/-=Schwelle, s=speichern)"
    )

update_title()
ax.set_xlabel("Spalte")
ax.set_ylabel("Zeile")

def on_key(event):
    global THRESHOLD, baseline_active
    if event.key == "b":
        capture_baseline()
    elif event.key == "r":
        baseline_active = False
        print("Baseline zurückgesetzt (Rohwerte).")
    elif event.key == "+":
        THRESHOLD += THRESHOLD_STEP
        print(f"Schwellwert = {THRESHOLD}")
    elif event.key == "-":
        THRESHOLD = max(0, THRESHOLD - THRESHOLD_STEP)
        print(f"Schwellwert = {THRESHOLD}")
    elif event.key == "s":
        fname = f"frame_kalibriert_{int(time.time())}.csv"
        np.savetxt(fname, data, delimiter=",", fmt="%d")
        print(f"Kalibrierter Frame gespeichert: {fname}")
    elif event.key == "x":
        fname = f"frame_roh_{int(time.time())}.csv"
        np.savetxt(fname, raw_data, delimiter=",", fmt="%d")
        print(f"Roh-Frame gespeichert: {fname}")
    update_title()

fig.canvas.mpl_connect("key_press_event", on_key)

def update(_frame_num):
    global data, raw_data
    frame = read_frame()
    if frame is not None:
        raw_data = frame
        data = calibrate(frame)
        im.set_data(data)
    return [im]

ani = FuncAnimation(fig, update, interval=50, cache_frame_data=False)
plt.tight_layout()
plt.show()

ser.close()