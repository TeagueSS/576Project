# IoT MQTT Simulation

This project implements a simplified IoT network simulator with BLE, Wi-Fi, and Zigbee PHYs, MQTT networking semantics, and a Tkinter-based dashboard. It is intended for coursework exploration of PHY/MAC fidelity, MQTT behavior, mobility, topology changes, and experiment design.

## Requirements

- Python 3.11+
- Packages: `pip install -r requirements.txt`

## Running

```bash
python main.py
```

The GUI launches with controls to run simulations, trigger broker failover events, and export collected metrics as CSV files.

## GUI Overview

- **Geographic Map**: Displays node positions across the simulation area.
- **Topic Heatmap**: Shows message rates per topic (msgs/sec).
- **Broker Queue Sparkline**: Monitors queue depth over time.
- **Client State Table**: Lists each client with PHY, topic, current state, and cumulative energy.
- **Statistics Panel**: Summaries of delivery ratio, latency, duplicates, and energy consumption.
- **Controls**: run/pause, broker failover, and data export.

## Experiments

Three built-in experiment scenarios:

1. **E1 Duty Cycle Impact**: Varies Zigbee duty cycle and logs latency vs battery life.
2. **E2 Protocol Comparison**: Compares BLE, Wi-Fi, and Zigbee for delivery/latency/energy.
3. **E3 Topology Change & Broker Failure**: Evaluates recovery time and message loss with persistent sessions.

Results are written to `exports/` with CSV summaries for reproducibility.

## Deliverables Checklist

- Code + README (this file): complete.
- Design doc: `docs/design.md` (up to 5 pages) – architecture, models, assumptions.
- Experiment report: `docs/experiment_report.md` (up to 5 pages) – E1/E2/E3 results & insights.
- Reproducible artifacts: configs, generated CSVs under `exports/`, and plotting notebooks under `notebooks/`.

See `docs/` for details and commands.


