## Experiment Report – E1/E2/E3

### E1: Duty Cycle Impact
- Setup: baseline vs `duty_cycle` (Zigbee 5%).
- Metrics: delivery, latency, energy, avg sleep ratio, battery days.
- Expected: higher sleep ratio and battery life at expense of latency.

### E2: Protocol Comparison
- Setup: `ble_only`, `wifi_only`, `zigbee_only`.
- Metrics: delivery, latency, energy.
- Expected: Wi‑Fi lowest latency/highest energy; Zigbee most efficient; BLE middle.

### E3: Topology & Broker Failover
- Setup: `topology_failover_clean` vs `topology_failover_persist`.
- Metrics: delivery dip, duplicates, queue drops, time‑to‑restore.
- Expected: persistent sessions restore faster with fewer losses.

### Reproducibility
- Use GUI Composite tab to run each study; export CSV from Results/Composite tabs.
- CSVs will be placed under `exports/`.


