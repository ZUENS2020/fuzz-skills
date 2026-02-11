import os
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def file_lock(lock_path: Path, timeout_s: float = 10.0, poll_s: float = 0.1):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    fd = None
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            break
        except FileExistsError:
            if time.time() - start > timeout_s:
                raise TimeoutError(f"Timed out waiting for lock: {lock_path}")
            time.sleep(poll_s)
    try:
        yield
    finally:
        try:
            if fd is not None:
                os.close(fd)
            if lock_path.exists():
                lock_path.unlink()
        except OSError:
            pass
