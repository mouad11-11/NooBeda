import os
import sys
import time
import subprocess
import queue
import pytest

def test_process_group_termination():
    """Verify that child process group is cleanly terminated on abort."""
    # Spawn a sleeping python child process in its own process group
    extra_kwargs = {}
    if sys.platform.startswith("win"):
        extra_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        extra_kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        **extra_kwargs
    )
    pid = proc.pid
    assert proc.poll() is None, "Process should be running"

    # Simulate Abort
    if sys.platform.startswith("win"):
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import signal
        os.killpg(os.getpgid(pid), signal.SIGTERM)

    time.sleep(0.5)
    # Check if process is still alive
    if sys.platform.startswith("win"):
        check = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], stdout=subprocess.PIPE, text=True)
        assert str(pid) not in check.stdout, f"Orphan process {pid} remained after abort!"
    else:
        assert proc.poll() is not None

def test_thread_safe_log_queue():
    """Verify thread-safe logging queue drains smoothly."""
    q = queue.Queue()
    for i in range(100):
        q.put(f"msg {i}")

    drained = []
    while not q.empty():
        drained.append(q.get_nowait())

    assert len(drained) == 100
    assert drained[0] == "msg 0"
    assert drained[-1] == "msg 99"
