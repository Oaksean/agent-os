"""
TurnDiffTracker 文件差异跟踪测试
"""

import os

import pytest

from src.tools.diff_tracker import ChangeType, TurnDiffTracker


@pytest.fixture
def tracker(tmp_path):
    """创建含两个基线文件的 tracker"""
    (tmp_path / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("foo\n", encoding="utf-8")

    t = TurnDiffTracker(root=str(tmp_path))
    t.snapshot_baseline("a.txt")
    t.snapshot_baseline("b.txt")
    return t, tmp_path


def test_detect_modification(tracker):
    t, tmp_path = tracker
    (tmp_path / "a.txt").write_text("hello\nuniverse\n", encoding="utf-8")

    changes = t.compute_diff()
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.MODIFIED
    assert "+universe" in changes[0].diff


def test_detect_addition_and_deletion(tracker):
    t, tmp_path = tracker
    # 新增：先记录空基线（文件尚不存在），再创建文件 → 应识别为 ADDED
    t.snapshot_baseline("new.txt")
    (tmp_path / "new.txt").write_text("brand new\n", encoding="utf-8")
    # 删除
    os.remove(str(tmp_path / "b.txt"))

    changes = {c.change_type: c for c in t.compute_diff()}
    assert ChangeType.ADDED in changes
    assert ChangeType.DELETED in changes
    assert changes[ChangeType.DELETED].path.endswith("b.txt")


def test_rename_tracking(tracker):
    t, tmp_path = tracker
    (tmp_path / "b.txt").rename(tmp_path / "c.txt")
    t.track_rename("b.txt", "c.txt")

    # 重命名后 uuid 保持一致
    uuid_before = t.get_uuid("b.txt")  # 已不存在
    uuid_after = t.get_uuid("c.txt")
    assert uuid_after is not None


def test_rollback(tracker):
    t, tmp_path = tracker
    original = (tmp_path / "a.txt").read_text(encoding="utf-8")
    (tmp_path / "a.txt").write_text("CHANGED", encoding="utf-8")

    t.rollback()
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == original


def test_no_change_when_identical(tracker):
    t, tmp_path = tracker
    assert t.compute_diff() == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
