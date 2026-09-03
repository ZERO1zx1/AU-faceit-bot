"""Structured identifier helpers and constants."""


def _btn(component: str, action: str) -> str:
    return f"au:{component}:{action}"


BUTTON_IDS = {
    "register": _btn("register", "open"),
    "queue_join": _btn("queue", "join"),
    "queue_leave": _btn("queue", "leave"),
    "result_submit": _btn("result", "submit"),
    "result_approve": _btn("result", "approve"),
    "result_reject": _btn("result", "reject"),
    "unregister_confirm": _btn("player", "unregister_confirm"),
    "unregister_cancel": _btn("player", "unregister_cancel"),
}


def with_entity(action: str, entity: str) -> str:
    return f"{action}:{entity}"
