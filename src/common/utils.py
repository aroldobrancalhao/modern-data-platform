from datetime import datetime


def current_timestamp() -> str:

    return datetime.utcnow().isoformat()
