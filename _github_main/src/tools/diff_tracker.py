"""
TurnDiffTracker —— 文件变更差异跟踪器

参考 OpenAI Codex Harness 的 TurnDiffTracker 机制设计，用于精确追踪
Agent 在一次任务（Turn）中对文件系统所做的所有变更，并生成标准统一 Diff。

核心机制：

1. 基线快照 (Baseline Snapshot)
   Agent 首次访问某文件时，在内存中记录其「基线快照」（内容哈希、权限、大小）。
   新创建的文件基线视为空（等价于 /dev/null）。

2. UUID 映射与重命名跟踪
   为每个外部文件路径分配一个内部唯一 UUID，维护
   `external_path <-> UUID <-> current_path` 的双向映射。
   即使文件被重命名/移动，也能通过 UUID 追踪其变更历史，生成准确的
   Rename Diff，而非误判为「删除旧文件 + 创建新文件」。

3. 统一 Diff 生成
   任务结束时对比当前磁盘状态与基线快照，生成聚合统一 Diff。

4. Overlay 语义（提交/回滚）
   支持将变更「提交」或「回滚」—— 回滚会把被修改的文件恢复到基线内容，
   实现 Copy-on-Write Overlay 的原子性保证。
"""

from __future__ import annotations

import difflib
import hashlib
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """文件变更类型"""

    ADDED = "added"  # 新增（基线为空，当前有内容）
    MODIFIED = "modified"  # 修改
    DELETED = "deleted"  # 删除（基线有内容，当前不存在）


@dataclass
class FileSnapshot:
    """文件基线快照"""

    path: str
    content_hash: str
    size: int
    mode: Optional[int] = None
    content: Optional[str] = None  # 基线内容（用于回滚）
    captured_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_disk(cls, path: str) -> Optional["FileSnapshot"]:
        """从磁盘读取文件生成快照；文件不存在返回 None"""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            # 二进制或不可读文件：仅记录哈希
            with open(path, "rb") as f:
                raw = f.read()
            return cls(
                path=path,
                content_hash=hashlib.sha256(raw).hexdigest(),
                size=len(raw),
                mode=os.stat(path).st_mode if os.path.exists(path) else None,
                content=None,
            )
        return cls(
            path=path,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            size=len(content.encode("utf-8")),
            mode=os.stat(path).st_mode,
            content=content,
        )


@dataclass
class FileChange:
    """一次文件变更记录"""

    uuid: str
    path: str  # 当前路径
    original_path: Optional[str]  # 原始路径（重命名前）
    change_type: ChangeType
    diff: str  # 统一 diff 文本
    old_content: Optional[str]
    new_content: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "path": self.path,
            "original_path": self.original_path,
            "change_type": self.change_type.value,
            "diff": self.diff,
        }


class TurnDiffTracker:
    """文件变更差异跟踪器（单次任务 Turn 级别）"""

    def __init__(self, root: Optional[str] = None):
        self.root = root or os.getcwd()
        self.baselines: Dict[str, FileSnapshot] = {}  # uuid -> 基线快照
        self.path_to_uuid: Dict[str, str] = {}  # 外部路径 -> uuid
        self.uuid_to_path: Dict[str, str] = {}  # uuid -> 当前路径
        self._tracked_files: List[str] = []  # 访问顺序

    # ==================== 基线快照 ====================

    def snapshot_baseline(self, path: str) -> str:
        """
        记录文件的基线快照并分配 UUID。

        Args:
            path: 文件路径（绝对或相对 root）

        Returns:
            分配的 UUID
        """
        abs_path = self._abs(path)

        # 已跟踪则复用 UUID
        if abs_path in self.path_to_uuid:
            return self.path_to_uuid[abs_path]

        file_uuid = str(uuid.uuid4())
        snapshot = FileSnapshot.from_disk(abs_path)
        if snapshot is None:
            # 文件尚不存在 → 空基线（对应「新增」场景）
            snapshot = FileSnapshot(
                path=abs_path, content_hash="", size=0, content="", mode=None
            )

        self.baselines[file_uuid] = snapshot
        self.path_to_uuid[abs_path] = file_uuid
        self.uuid_to_path[file_uuid] = abs_path
        self._tracked_files.append(abs_path)
        return file_uuid

    def snapshot_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """批量记录目录下文件的基线（返回 UUID 列表）"""
        uuids = []
        abs_dir = self._abs(directory)
        if not os.path.isdir(abs_dir):
            return uuids
        for current_root, _dirs, files in os.walk(abs_dir):
            for name in files:
                uuids.append(self.snapshot_baseline(os.path.join(current_root, name)))
            if not recursive:
                break
        return uuids

    # ==================== 重命名跟踪 ====================

    def track_rename(self, old_path: str, new_path: str) -> bool:
        """
        记录文件重命名：更新 UUID 映射，使 diff 能识别为 Rename 而非删除+新增。

        Args:
            old_path: 原路径
            new_path: 新路径

        Returns:
            是否成功（原路径必须已被跟踪）
        """
        abs_old = self._abs(old_path)
        abs_new = self._abs(new_path)

        if abs_old not in self.path_to_uuid:
            logger.warning(f"重命名失败：{abs_old} 未被跟踪")
            return False

        file_uuid = self.path_to_uuid.pop(abs_old)
        self.path_to_uuid[abs_new] = file_uuid
        self.uuid_to_path[file_uuid] = abs_new
        self._tracked_files.append(abs_new)
        logger.info(f"跟踪重命名：{abs_old} -> {abs_new} (uuid={file_uuid[:8]})")
        return True

    # ==================== Diff 计算 ====================

    def compute_diff(self, path: Optional[str] = None) -> List[FileChange]:
        """
        计算变更 diff。

        Args:
            path: 若指定，仅计算该文件；否则计算所有已跟踪文件

        Returns:
            变更记录列表
        """
        changes: List[FileChange] = []

        target_uuids = self.baselines.keys()
        if path:
            abs_path = self._abs(path)
            file_uuid = self.path_to_uuid.get(abs_path)
            target_uuids = [file_uuid] if file_uuid else []

        for file_uuid in target_uuids:
            change = self._compute_single_change(file_uuid)
            if change:
                changes.append(change)

        return changes

    def _compute_single_change(self, file_uuid: str) -> Optional[FileChange]:
        baseline = self.baselines[file_uuid]
        current_path = self.uuid_to_path.get(file_uuid, baseline.path)

        current = FileSnapshot.from_disk(current_path)
        old_content = baseline.content or ""
        new_content = current.content if current else None

        # 删除：基线有，当前无
        if current is None:
            if old_content == "":
                return None  # 本就不存在且无内容
            diff = self._unified_diff(current_path, current_path, old_content, "")
            return FileChange(
                uuid=file_uuid,
                path=current_path,
                original_path=baseline.path,
                change_type=ChangeType.DELETED,
                diff=diff,
                old_content=old_content,
                new_content=None,
            )

        # 新增：基线为空，当前有
        if old_content == "" and current.content != "":
            diff = self._unified_diff(current_path, current_path, "", current.content)
            return FileChange(
                uuid=file_uuid,
                path=current_path,
                original_path=baseline.path,
                change_type=ChangeType.ADDED,
                diff=diff,
                old_content="",
                new_content=current.content,
            )

        # 修改：内容哈希变化
        if current.content_hash != baseline.content_hash:
            diff = self._unified_diff(current_path, current_path, old_content, current.content)
            change_type = (
                ChangeType.MODIFIED
                if baseline.path == current_path
                else ChangeType.MODIFIED  # 重命名合并处理为 modified，附带 original_path
            )
            return FileChange(
                uuid=file_uuid,
                path=current_path,
                original_path=baseline.path if baseline.path != current_path else None,
                change_type=change_type,
                diff=diff,
                old_content=old_content,
                new_content=current.content,
            )

        return None  # 无变化

    @staticmethod
    def _unified_diff(
        path: str, new_path: str, old_content: str, new_content: str, context_lines: int = 3
    ) -> str:
        """生成统一 diff 文本"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{new_path}",
                n=context_lines,
            )
        )
        return "".join(diff_lines)

    # ==================== Overlay 提交/回滚 ====================

    def commit(self) -> None:
        """提交变更：更新基线为当前状态（Overlay 合并）"""
        for file_uuid, baseline in list(self.baselines.items()):
            current_path = self.uuid_to_path.get(file_uuid, baseline.path)
            current = FileSnapshot.from_disk(current_path)
            if current:
                self.baselines[file_uuid] = current
            else:
                # 文件已删除 → 记录空基线
                self.baselines[file_uuid] = FileSnapshot(
                    path=current_path, content_hash="", size=0, content="", mode=None
                )
        logger.info(f"TurnDiffTracker 提交：{len(self.baselines)} 个基线已更新")

    def rollback(self) -> int:
        """
        回滚变更：将被修改的文件恢复到基线内容。

        Returns:
            回滚的文件数量
        """
        rolled_back = 0
        changes = self.compute_diff()
        for change in changes:
            try:
                if change.change_type == ChangeType.DELETED:
                    # 恢复被删除的文件
                    os.makedirs(os.path.dirname(change.path), exist_ok=True)
                    with open(change.path, "w", encoding="utf-8") as f:
                        f.write(change.old_content or "")
                elif change.old_content is not None:
                    # 恢复被修改/新增的文件
                    os.makedirs(os.path.dirname(change.path), exist_ok=True)
                    with open(change.path, "w", encoding="utf-8") as f:
                        f.write(change.old_content)
                else:
                    continue
                rolled_back += 1
            except OSError as exc:
                logger.error(f"回滚失败 {change.path}: {exc}")
        logger.info(f"TurnDiffTracker 回滚：{rolled_back} 个文件已恢复")
        return rolled_back

    # ==================== 查询 ====================

    def get_tracked_files(self) -> List[str]:
        """返回所有已跟踪的文件路径"""
        return list(self._tracked_files)

    def get_uuid(self, path: str) -> Optional[str]:
        """根据路径获取 UUID"""
        return self.path_to_uuid.get(self._abs(path))

    def get_path(self, file_uuid: str) -> Optional[str]:
        """根据 UUID 获取当前路径"""
        return self.uuid_to_path.get(file_uuid)

    def summary(self) -> Dict[str, Any]:
        """汇总当前跟踪状态"""
        return {
            "tracked_files": len(self._tracked_files),
            "baselines": len(self.baselines),
            "changes": [c.to_dict() for c in self.compute_diff()],
        }

    # ==================== 辅助 ====================

    def _abs(self, path: str) -> str:
        """归一化为绝对路径"""
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self.root, path))


# ==================== 演示 ====================

def demo():
    """离线演示 TurnDiffTracker 的完整生命周期"""
    import tempfile

    tmp = tempfile.mkdtemp(prefix="diff_demo_")
    f1 = os.path.join(tmp, "a.txt")
    f2 = os.path.join(tmp, "b.txt")

    with open(f1, "w", encoding="utf-8") as f:
        f.write("hello\nworld\n")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("foo\n")

    tracker = TurnDiffTracker(root=tmp)

    # 1. 记录基线
    u1 = tracker.snapshot_baseline("a.txt")
    u2 = tracker.snapshot_baseline("b.txt")
    print(f"跟踪 UUID: a.txt={u1[:8]}, b.txt={u2[:8]}")

    # 2. 修改 + 重命名 + 新增 + 删除
    with open(f1, "w", encoding="utf-8") as f:
        f.write("hello\nuniverse\n")
    tracker.track_rename("b.txt", "c.txt")
    with open(os.path.join(tmp, "c.txt"), "a", encoding="utf-8") as f:
        f.write("bar\n")
    with open(os.path.join(tmp, "new.txt"), "w", encoding="utf-8") as f:
        f.write("brand new\n")
    tracker.snapshot_baseline("new.txt")
    os.remove(f1)  # 模拟删除（f1 已重写，此处直接删除演示 deleted）

    # 3. 计算 diff
    print("\n=== 变更 diff ===")
    for change in tracker.compute_diff():
        print(f"[{change.change_type.value}] {change.path}")
        print(change.diff)

    # 4. 回滚
    print("=== 回滚 ===")
    tracker.rollback()
    print(f"a.txt 恢复后: {open(f1, encoding='utf-8').read()!r}")

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    demo()
