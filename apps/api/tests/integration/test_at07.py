"""AT-07 (image blocks) is P1; kept as an explicit skip so the AT-01..14 list is complete."""
import pytest


@pytest.mark.skip(reason="P1 image, ngoài phạm vi P0")
def test_at07_image_blocks() -> None:
    raise AssertionError("AT-07 is not implemented")
