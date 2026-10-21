from dataclasses import replace

import pytest

from droidasc_mcp.native_page import SortedPage
from droidasc_mcp.runner import DroidAscError


@pytest.mark.parametrize("offset", [0, 2, 4096, 2**64])
def test_page_is_stable_bounded_and_owned(settings, tmp_path, offset):
    rows = [(bytes([i % 3]), b"", 0) for i in range(5000)]
    expected = sorted(enumerate(rows), key=lambda row: (row[1], row[0]))
    with SortedPage(settings, offset, 3, tmp_path) as page:
        if page.directory:
            assert str(page.directory.name).startswith(str(tmp_path))
        for i, key in enumerate(rows):
            page.add(key, {"row": i})
        assert page.items() == [{"row": i} for i, _ in expected[offset : offset + 3]]
        assert page.total == 5000
        assert len(page.heap) <= min(offset + 3, 4096)
    assert not list(tmp_path.iterdir())


def test_spool_disk_budget_is_enforced_and_cleaned(settings, tmp_path):
    settings = replace(settings, max_xref_index_bytes=4096 * 3)
    with (
        pytest.raises(DroidAscError, match="disk budget"),
        SortedPage(settings, 4096, 1, tmp_path) as page,
    ):
        for i in range(100):
            page.add((b"a", b"", i), {"text": "a" * 4096})
    assert not list(tmp_path.iterdir())
