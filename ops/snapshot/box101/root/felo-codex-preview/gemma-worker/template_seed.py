"""Bounded, checksum-verified text copies. No parent state or runtime data."""
import hashlib
import re


def validate_seed(value):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'files', 'digest'}:
        raise ValueError('Invalid template seed')
    files = value['files']
    if not isinstance(files, list) or not 1 <= len(files) <= 12:
        raise ValueError('Invalid template file count')
    seen, total, result = set(), 0, []
    for item in files:
        if not isinstance(item, dict) or set(item) != {'path', 'content'}:
            raise ValueError('Invalid template file')
        name, content = item['path'], item['content']
        if (not isinstance(name, str) or len(name) > 180 or
                not re.fullmatch(r'[-a-zA-Z0-9_./]+', name) or
                any(not p or p.startswith('.') for p in name.split('/')) or
                not re.search(r'\.(html|css|js|json|svg|md|txt)$', name) or
                name in ('report.md', 'felo-data.js') or name in seen):
            raise ValueError('Invalid template path')
        if not isinstance(content, str) or '\0' in content:
            raise ValueError('Invalid template text')
        total += len(content.encode('utf-8'))
        if total > 48000:
            raise ValueError('Template exceeds coding context limit')
        seen.add(name)
        result.append({'path': name, 'content': content})
    if 'index.html' not in seen or any(b.startswith(a + '/') for a in seen for b in seen):
        raise ValueError('Template entry point or directory conflict')
    result.sort(key=lambda f: f['path'])
    digest = hashlib.sha256(''.join(f['path'] + '\0' + hashlib.sha256(f['content'].encode()).hexdigest() + '\n' for f in result).encode()).hexdigest()
    if value['digest'] != digest:
        raise ValueError('Template checksum mismatch')
    return {'files': result, 'digest': digest}


def copy_seed(value, workspace):
    value = validate_seed(value)
    if value:
        for file in value['files']:
            target = workspace / file['path']
            if not target.resolve().is_relative_to(workspace.resolve()):
                raise ValueError('Template destination escaped workspace')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file['content'], encoding='utf-8', newline='')
            if target.read_bytes() != file['content'].encode('utf-8'):
                raise ValueError('Template copy verification failed')
