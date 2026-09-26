"""Snapshot preview worker artifacts and SQLite; verify an inert restore on container 101.

Fixed preview paths only. No credentials, service restarts or job replay.
Archive and restored files stay private on the server. Abort if artifacts change.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tarfile
import uuid

SOURCE = Path('/root/felo-codex-preview/gemma-worker/jobs')
RECOVERY = Path('/root/felo-codex-preview/gemma-worker/recovery')
ID = re.compile(r'^[a-f0-9]{32}$')
MAX_BYTES = 256 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def artifact_manifest():
    result = {}
    size = 0
    for directory in sorted(SOURCE.iterdir()):
        if directory.name in ('preview-data.sqlite', 'preview-data.sqlite-wal',
                               'preview-data.sqlite-shm', 'preview-data.sqlite-journal'):
            continue
        if directory.is_symlink() or not directory.is_dir() or not ID.fullmatch(directory.name):
            raise RuntimeError('Unexpected worker entry; review before backing up')
        state = json.loads((directory / 'state.json').read_text())
        if state.get('status') in ('queued', 'running'):
            raise RuntimeError('A preview job is active; retry after it finishes')
        for path in sorted(directory.rglob('*')):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise RuntimeError('Worker archive cannot include links or special files')
            if path.is_file():
                size += path.stat().st_size
                if size > MAX_BYTES:
                    raise RuntimeError('Worker artifacts exceed the recovery exercise limit')
                result[path.relative_to(SOURCE).as_posix()] = digest(path)
    return result


def db_fingerprint(path):
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise RuntimeError('SQLite integrity check failed')
        schema = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        tables = [r[1] for r in schema if r[0] == 'table' and not r[1].startswith('sqlite_')]
        if tables != ['records']:
            raise RuntimeError('Unexpected SQLite schema; extend restore verification first')
        rows = db.execute('SELECT app,collection,id,version,data FROM records ORDER BY app,collection,id').fetchall()
        encoded = json.dumps({'schema':schema,'rows':rows}, ensure_ascii=False, separators=(',', ':')).encode()
        return {'rows':len(rows),'content_sha256':hashlib.sha256(encoded).hexdigest()}


def main():
    os.umask(0o077)
    if SOURCE.is_symlink() or SOURCE.resolve() != SOURCE or not SOURCE.is_dir():
        raise RuntimeError('Expected fixed preview worker directory')
    RECOVERY.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = RECOVERY / (stamp + '-' + uuid.uuid4().hex[:8])
    folder.mkdir(mode=0o700)
    evidence = {'started_at':stamp,'verified':False,'production_changed':False,
                'jobs_executed':False,'credentials_included':False,'backup_folder':str(folder)}
    try:
        before = artifact_manifest()
        db_path = SOURCE / 'preview-data.sqlite'
        if db_path.is_symlink() or not db_path.is_file() or db_path.stat().st_size > MAX_BYTES:
            raise RuntimeError('Expected bounded preview SQLite database')
        backup_db = folder / 'preview-data.sqlite'
        with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as src:
            with sqlite3.connect(backup_db) as dest:
                src.backup(dest)
        expected_db = db_fingerprint(backup_db)
        archive = folder / 'worker-artifacts.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            for name in before:
                tar.add(SOURCE / name, arcname=name, recursive=False)
        if artifact_manifest() != before:
            raise RuntimeError('Worker changed during backup; this snapshot is not verified')
        restored = folder / 'restored'
        restored.mkdir(mode=0o700)
        seen = set()
        with tarfile.open(archive, 'r:gz') as tar:
            for member in tar:
                if member.name not in before or member.name in seen or not member.isfile():
                    raise RuntimeError('Unexpected archive member')
                dest = restored / member.name
                if not dest.resolve().is_relative_to(restored.resolve()):
                    raise RuntimeError('Archive member escaped the restore directory')
                dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with tar.extractfile(member) as src, dest.open('xb') as out:
                    while chunk := src.read(1024 * 1024):
                        out.write(chunk)
                if digest(dest) != before[member.name]:
                    raise RuntimeError('Restored artifact content differs')
                seen.add(member.name)
        if seen != set(before):
            raise RuntimeError('Missing restored artifact')
        restored_db = restored / 'preview-data.sqlite'
        restored_db.write_bytes(backup_db.read_bytes())
        if db_fingerprint(restored_db) != expected_db:
            raise RuntimeError('Restored application data differs')
        evidence.update(verified=True,artifact_files=len(before),
                        jobs=len({x.split('/')[0] for x in before}),
                        sqlite=expected_db,archive_sha256=digest(archive),
                        sqlite_sha256=digest(backup_db),archive_bytes=archive.stat().st_size)
        (folder / 'artifact-manifest.json').write_text(json.dumps(before, indent=2)+'\n')
        print(json.dumps(evidence))
    finally:
        (folder / 'verification.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
