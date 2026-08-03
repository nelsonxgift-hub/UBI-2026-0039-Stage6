import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor-verifier"))


def copy_input_writable(src: Path, dst: Path) -> None:
    """
    submission-contract.md requires input/ to be locked read-only (chmod 444)
    once hashed. shutil.copytree preserves that permission bit by default, so
    a plain copytree of a locked input/ produces an equally read-only scratch
    copy -- any write to it then raises PermissionError for a normal user
    (root bypasses the write-permission bit entirely on Linux, which is why
    this silently worked in a root-run sandbox and failed on a real account).
    This copies, then explicitly restores owner-write on every file in the
    SCRATCH copy only; the real input/ directory is left untouched and stays
    locked.
    """
    shutil.copytree(src, dst)
    for path in dst.rglob("*"):
        if path.is_file():
            path.chmod(path.stat().st_mode | stat.S_IWUSR)
