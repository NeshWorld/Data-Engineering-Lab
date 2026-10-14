"""SQLite connections with explicit commit/rollback AND closure on Windows."""
import sqlite3
from contextlib import contextmanager

@contextmanager
def database(path, **kwargs):
    connection = sqlite3.connect(path, **kwargs)
    try:
        with connection:
            yield connection
    finally:
        connection.close()



def backup_database(source, destination, timeout=5):
    """Bound busy retries as well as SQL execution (external IDE locks)."""
    import time
    started=time.monotonic()
    def progress(*_):
        if time.monotonic()-started > timeout:
            raise TimeoutError('Copie SQLite interrompue : base occupée ou trop volumineuse.')
    source.backup(destination,pages=256,progress=progress,sleep=.02)


def publish_files(replacements):
    """Publish a small local file bundle; roll back ordinary replacement failures.

    Backups remain alongside their targets if rollback itself fails. This is
    exception-safe, not a crash-atomic transaction spanning multiple files.
    """
    import os
    from pathlib import Path
    import shutil
    import tempfile
    backups={}
    published=[]
    preserve=False
    try:
        for staged,target in replacements:
            target=Path(target)
            if target.exists():
                handle=tempfile.NamedTemporaryFile(prefix='.rollback-',dir=target.parent,delete=False)
                backup=Path(handle.name)
                handle.close()
                backups[target]=backup
                shutil.copy2(target,backup)
            else:
                backups[target]=None
        for staged,target in replacements:
            os.replace(staged,target)
            published.append(Path(target))
    except Exception as original:
        failed=[]
        for target in reversed(published):
            try:
                backup=backups[target]
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(backup,target)
            except OSError:
                failed.append(str(target))
        if failed:
            preserve=True
            raise RuntimeError('Restauration automatique impossible pour '+', '.join(failed)+'. Sauvegardes .rollback- conservées à côté des fichiers ; fermez les outils externes.') from original
        raise
    finally:
        if not preserve:
            for backup in backups.values():
                if backup is not None:
                    backup.unlink(missing_ok=True)
