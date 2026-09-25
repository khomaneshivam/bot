import os
import sys
import webbrowser
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# Ensure the root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    print("=" * 65)
    print(" 🚀 QuantAI | Autonomous Forex & Crypto Trading Terminal")
    print(" 🧠 Neural Model | Continuous Live Retraining | Negative Shield")
    print(" 💼 Modes: [Paper Trading] | [Demo Account] | [Live Account]")
    print("=" * 65)
    
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "8000"))
    url = f"http://localhost:{port}" if host == "0.0.0.0" else f"http://{host}:{port}"
    print(f"\n🌐 Dashboard running at: {url}")
    print(f"📡 API & Telemetry bound to: {host}:{port}\n")
    
    if host == "127.0.0.1" and sys.platform == "win32":
        try:
            webbrowser.open(url)
        except Exception:
            pass
        
    uvicorn.run("server.app:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
