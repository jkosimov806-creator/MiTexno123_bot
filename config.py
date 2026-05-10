import os

def get_admin_ids() -> set[int]:
    raw = os.environ.get("ADMIN_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def is_admin(user_id: int) -> bool:
    admins = get_admin_ids()
    if not admins:
        return False
    return user_id in admins
