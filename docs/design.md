## IoT MQTT Simulation – Design Document

This document describes the system architecture, abstractions, and modeling choices.

### 1. Architecture Overview
- GUI (Tkinter): map, metrics, composite experiments.
- Simulation core (SimPy): MAC, Network (MQTT), Mobility, Metrics.
- Config factory: scenarios and topology variations (E1/E2/E3).

### 2. PHY/MAC Models
- PHY profiles (BLE 5.x, Wi‑Fi 802.11n, Zigbee 802.15.4): data rate, power, range, latency, Zigbee duty cycle.
- MAC:
  - BLE: connection-event alignment, sleep between events; supervision timeout considered by reconnect logic.
  - Wi‑Fi/Zigbee: CSMA/CA backoff and single ACK retry approximation.

### 3. MQTT/Network
- QoS0/1 with DUP retransmits, retained messages, LWT.
- Keep-alive + reconnect with exponential backoff, session resume when `clean_session=False`.
- Gateway hop adds WAN latency/loss; broker queue capacity enforced.

### 4. Mobility
- ≥70% stationary nodes; mobile nodes with Grid or Random Waypoint.
- Moving gateways optionally emulate coverage changes.

### 5. Metrics
- Delivery ratio, E2E latency, duplicates, energy, topic rates, queue depth.
- Battery days estimate; radio time (tx/rx/sleep) and average sleep ratio.
- Queue drops; failover/restore timing placeholder.

### 6. Experiments
- E1 Duty Cycle: baseline vs 5% Zigbee duty cycle → sleep ratio, latency, battery.
- E2 Protocols: BLE vs Wi‑Fi vs Zigbee → delivery, latency, energy.
- E3 Failover/Topology: baseline vs failover; persistent vs clean sessions; time‑to‑restore and message loss.

### 7. Reproducibility
- Deterministic rng seeding; configs via `sim/config_factory.py`.
- Exports as CSV; plots via notebooks in `/notebooks`.


