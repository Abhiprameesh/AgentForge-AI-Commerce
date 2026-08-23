import json
import os
from datetime import datetime

AUDIT_LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "audit_logs.json"))

def log_event(session_id: str, agent: str, action: str, input_data: str | dict, output_data: str | dict, tool: str = None, result: str = None, user_confirmation: bool = False):
    """
    Log an agent action or system event to the audit trail.
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "agent": agent,
        "action": action,
        "input": input_data if isinstance(input_data, str) else json.dumps(input_data),
        "output": output_data if isinstance(output_data, str) else json.dumps(output_data),
        "tool": tool,
        "result": result,
        "user_confirmation": user_confirmation
    }

    try:
        logs = []
        if os.path.exists(AUDIT_LOG_PATH):
            with open(AUDIT_LOG_PATH, "r") as f:
                logs = json.load(f)
        
        logs.append(event)
        
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "w") as f:
            json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"Failed to write audit log: {e}")

def get_session_logs(session_id: str) -> list[dict]:
    """Retrieve audit logs for a specific session."""
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
    try:
        with open(AUDIT_LOG_PATH, "r") as f:
            logs = json.load(f)
            return [log for log in logs if log.get("session_id") == session_id]
    except Exception:
        return []

def get_all_logs() -> list[dict]:
    """Retrieve all audit logs."""
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
    try:
        with open(AUDIT_LOG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []
