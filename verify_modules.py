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

print(f"Checking modules in {project_root}")

try:
    from Modules.ai_chat import setup_module as setup_ai
    print("✅ AI Chat module imported successfully")
except Exception as e:
    print(f"❌ Failed to import AI Chat: {e}")

try:
    from Modules.broadcast import setup_module as setup_broadcast
    print("✅ Broadcast module imported successfully")
except Exception as e:
    print(f"❌ Failed to import Broadcast: {e}")
