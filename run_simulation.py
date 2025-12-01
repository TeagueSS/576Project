import sys
import os

# 1. Add the project root directory to Python's search path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. Import the new App class
# We import ModernIotApp but alias it as IotSimulationApp so it matches expectations
from src.gui.app import ModernIotApp as IotSimulationApp

if __name__ == "__main__":
    print(f"Starting Simulation from: {project_root}")
    app = IotSimulationApp()
    app.mainloop()

