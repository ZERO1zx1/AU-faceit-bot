"""Tests for structured custom-id helpers."""

from app.utils.ids import BUTTON_IDS, with_entity


def test_button_ids_structured():
    assert BUTTON_IDS["queue_join"] == "au:queue:join"
    assert BUTTON_IDS["result_approve"] == "au:result:approve"


def test_with_entity():
    assert with_entity(BUTTON_IDS["result_approve"], "42") == "au:result:approve:42"
