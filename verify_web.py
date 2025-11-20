import sys
import os
from pathlib import Path

# Add project root and Systems to sys.path
project_root = Path(os.getcwd())
systems_path = project_root / "Systems"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(systems_path) not in sys.path:
    sys.path.insert(0, str(systems_path))

print(f"Checking Web Panel in {project_root}")

try:
    from Systems.web.app import create_app
    print("✅ Web Panel backend imported successfully")
except Exception as e:
    print(f"❌ Failed to import Web Panel: {e}")
