import os
import shutil
import threading
import time
from pathlib import Path
from typing import List, Dict, Callable, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import platform

class FileOperationError(Exception):
    pass

class OptimisedFileOperations:
    """
    Optimised, concurrent, and atomic file operations with drive-based batching and rollback.
    Features:
    - Drive-based operation grouping
    - Concurrent execution (max 4 per drive)
    - Atomic moves for same-filesystem, copy+remove for cross-filesystem
    - Error handling and rollback
    - Progress and performance reporting
    - Cross-platform compatibility
    """
    def __init__(self, max_workers_per_drive: int = 4, batch_size: Optional[int] = None):
        self.max_workers_per_drive = max_workers_per_drive
        self.batch_size = batch_size or max_workers_per_drive
        self.operation_log: List[Dict] = []
        self.failed_operations: List[Dict] = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger("OptimisedFileOperations")

    @staticmethod
    def get_drive(path: Path) -> str:
        """Return a string representing the drive or mount point for grouping."""
        if platform.system() == "Windows":
            return str(path.drive).upper()
        else:
            # On Unix, use the device id (st_dev) as a proxy for the filesystem
            try:
                return str(os.stat(path).st_dev)
            except Exception:
                return str(path.anchor)

    @staticmethod
    def is_same_filesystem(src: Path, dst: Path) -> bool:
        """Detect if src and dst are on the same filesystem."""
        try:
            return os.stat(src).st_dev == os.stat(dst.parent).st_dev
        except Exception:
            return False

    def _move_atomic(self, src: Path, dst: Path) -> None:
        """Atomic move if possible."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.rename(src, dst)

    def _copy_and_remove(self, src: Path, dst: Path) -> None:
        """Copy then remove for cross-filesystem moves."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        os.remove(src)

    def _copy(self, src: Path, dst: Path) -> None:
        """Copy file."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def _execute_operation(self, op: Dict) -> Tuple[bool, Dict]:
        """Execute a single file operation with error handling."""
        src = Path(op['src'])
        dst = Path(op['dst'])
        op_type = op['type']
        start = time.time()
        try:
            if op_type == 'move':
                if self.is_same_filesystem(src, dst):
                    self._move_atomic(src, dst)
                else:
                    self._copy_and_remove(src, dst)
            elif op_type == 'copy':
                self._copy(src, dst)
            else:
                raise FileOperationError(f"Unknown operation type: {op_type}")
            elapsed = time.time() - start
            return True, {**op, 'status': 'success', 'elapsed': elapsed}
        except Exception as e:
            elapsed = time.time() - start
            self.logger.error(f"Failed {op_type} {src} -> {dst}: {e}")
            return False, {**op, 'status': 'failed', 'error': str(e), 'elapsed': elapsed}

    def batch_process(
        self,
        operations: List[Dict],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict]:
        """
        Batch process file operations with drive and type grouping, concurrency, and rollback log.
        Each operation dict: {'src': str, 'dst': str, 'type': 'move'|'copy'}
        """
        # Group by drive, then by operation type
        drive_groups: Dict[str, Dict[str, List[Dict]]] = {}
        for op in operations:
            drive = self.get_drive(Path(op['dst']))
            op_type = op['type']
            drive_groups.setdefault(drive, {}).setdefault(op_type, []).append(op)

        total_ops = len(operations)
        completed = 0
        results = []

        for drive, type_groups in drive_groups.items():
            for op_type, ops in type_groups.items():
                # Process in batches for this drive/type
                for i in range(0, len(ops), self.batch_size):
                    batch = ops[i:i+self.batch_size]
                    with ThreadPoolExecutor(max_workers=self.max_workers_per_drive) as executor:
                        future_to_op = {executor.submit(self._execute_operation, op): op for op in batch}
                        for future in as_completed(future_to_op):
                            success, result = future.result()
                            with self.lock:
                                self.operation_log.append(result)
                                if not success:
                                    self.failed_operations.append(result)
                                results.append(result)
                                completed += 1
                            if progress_callback:
                                progress_callback(completed, total_ops)
        return results

    def rollback(self) -> List[Dict]:
        """
        Attempt to undo successful operations in reverse order.
        Only supports rollback for moves (not copies).
        """
        rollback_results = []
        for op in reversed(self.operation_log):
            if op['status'] == 'success' and op['type'] == 'move':
                try:
                    # Move back if possible
                    src = Path(op['dst'])
                    dst = Path(op['src'])
                    if src.exists():
                        self._move_atomic(src, dst)
                        rollback_results.append({'src': str(src), 'dst': str(dst), 'status': 'rolled_back'})
                except Exception as e:
                    self.logger.error(f"Rollback failed for {src} -> {dst}: {e}")
                    rollback_results.append({'src': str(src), 'dst': str(dst), 'status': 'rollback_failed', 'error': str(e)})
        return rollback_results

    def get_operation_log(self) -> List[Dict]:
        """Return the operation log."""
        return list(self.operation_log)

    def get_failed_operations(self) -> List[Dict]:
        """Return the list of failed operations."""
        return list(self.failed_operations) 