# IoT Mesh Network Simulator - CS576 Project

This project is a discrete-event simulation tool built with Python and SimPy to analyze the behavior of IoT networks. It models MQTT-based communication across various wireless protocols (Zigbee, Wi-Fi, BLE) and visualizes mesh topology, node mobility, energy consumption, and broker failover scenarios in real-time.

## Features

*   **Multi-Protocol Simulation:** dynamic switching between Zigbee (Mesh/Low Power), Wi-Fi (High Bandwidth), and BLE (Short Range) physics layers.
*   **Visual Interface:** Interactive GUI showing node positions, signal ranges, and active transmissions.
*   **Live Metrics:** Real-time tracking of Packet Delivery Ratio (PDR), End-to-End Latency, Total Energy Consumption (Joules), and Broker Queue Depth.
*   **Failover Testing:** Simulation of catastrophic MQTT Broker crashes to observe client disconnection and exponential backoff reconnection logic.
*   **Configurable Physics:** Transmission power, range, and battery constraints are adjustable via external configuration files.

## Prerequisites

*   Python 3.8 or higher
*   pip (Python Package Manager)

## Installation and Setup

### 1. Set up a Virtual Environment
It is recommended to run the simulator in an isolated environment to prevent library conflicts.

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```
**MacOS / Linux**:
```
python3 -m venv venv
source venv/bin/activate
```
### 2. Install Dependencies
Install the required libraries with the command:
```
pip install -r requirements.txt
```

> [!NOTE]
> **For Linux Users:** If the GUI fails to launch, you may need to install the system-level Tkinter package (e.g., `sudo apt-get install python3-tk`).

## Running the Simulation
Execute the main script from the project root directory to launch the graphical interface:
```
python run_simulation.py
```
## User Guide
Here is the Markdown source code for the text you provided.


### Simulation Controls (Toolbar)

*   **START / PAUSE:** Toggles the simulation clock.
*   **RESET:** Clears all dynamic nodes and reloads the default scenario.
*   **PROTOCOL:** Selects the active physical layer properties. Changing this immediately updates the visual range indicators on the map.
*   **SPEED:** Adjusts the simulation time factor (0.1x to 10.0x real-time).
*   **FAILOVER:** Triggers a simulated Broker crash. All nodes will disconnect and attempt to reconnect after a random delay.

### Interactive Map

The main panel represents the simulation environment (scale is in meters).

*   **Adding Nodes:** Select a node type (Sensor, Mobile, or Gateway) from the tools panel and click on the canvas to place it.
*   **Selecting Nodes:** Choose "Select" mode and click any node to view its details in the side panel.
*   **Node Colors:**
    *   **Green:** Active and connected.
    *   **Red:** Disconnected or dead battery.
*   **Visual Aids:** Yellow lines indicate active message transmissions. Faint circles indicate the maximum wireless range based on the selected protocol.

### Inspector Panel

The right-side panel displays global network statistics:

*   **Delivery Ratio:** Percentage of published messages successfully received by subscribers.
*   **Avg Latency:** Time taken for a message to travel from Publisher to Broker to Subscriber.
*   **Total Energy:** Cumulative energy consumed by all nodes (TX/RX/Idle).
*   **Node Status Table:** A detailed list of all nodes, their current battery levels, and connection states.

## Configuration

Physics and network parameters can be modified without changing the source code. Edit the YAML files located in `src/configs/`:

*   `zigbee.yaml`: Settings for low-power, low-bandwidth mesh networks.
*   `wifi.yaml`: Settings for high-power, high-throughput networks.
*   `ble.yaml`: Settings for Bluetooth Low Energy.

**Example Configuration (`src/configs/zigbee.yaml`):**

```
range_m: 30             # Transmission range in meters
throughput_kbps: 250    # Data rate in kbps
tx_power_mw: 35         # Power consumption during transmission
rx_power_mw: 30         # Power consumption during reception
sleep_power_mw: 0.01    # Power consumption during sleep
```

## Project Structure

```text
.
├── run_simulation.py       # Main entry point for the application
└── src/
    ├── configs/            # YAML files defining radio physics profiles
    ├── devices/            # Logic for different node types
    ├── gui/                # Tkinter implementation for UI and plotting
    ├── mobility/           # Random waypoint algorithms for movement
    ├── mqtt/               # MQTT Broker and Client state machines
    ├── radios/             # Abstractions for TX time and energy costs
    └── sim/                # SimPy environment and global metrics
