import sys
import os

# 1. Add the project root directory to Python's search path
# This allows us to import from 'src' regardless of where this script is run from
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. Import the App using the full package path
# This ensures 'src.gui.app' is loaded as a module, allowing relative imports inside it to work
from src.gui.app import IotSimulationApp

if __name__ == "__main__":
    print(f"Starting Simulation from: {project_root}")
    app = IotSimulationApp()
    app.mainloop()