#!/usr/bin/env python3
"""Felo's dev team (step 2.5). Felo (Hermes) is the boss; Claude Code does the coding.

  build    <project> "<task>"   Claude Code (Daniel's Claude subscription) codes backend AND frontend
  review   <project>            what the last job changed + runs the project's tests (Felo checks the work)
  check-site <project>          website quality check: titles, descriptions, mobile tag, headings, alt text,
                                broken internal links, placeholder text, hotlinked images, heavy files
  local    "<instruction>" [file ...]   FREE: Gemma on Daniel's work PC reads/summarizes/translates/sorts text
                                (files, or text piped in). Use it before reading long text yourself.
  proposal-start <project> <CODE>   start a client proposal from the Felo Studio design (CODE = 3 letters, e.g. DGO)
  proposal-pdf   <project>          check the proposal has no blanks left, then make proposal.pdf
  jobs                          recent jobs and their status
  setup-check                   is Claude Code logged in?

Projects live in /workspace/projects/<project> (one git repo each; every job is one commit,
so any job can be undone with git revert). Job logs: /workspace/jobs/<job>/.
Claude Code may only read/write files in the project folder and run its tests: no other
commands, no deploys, pushes, emails or servers.
"""
import json, os, re, subprocess, sys, time, pathlib, urllib.request
from html.parser import HTMLParser

HOME = pathlib.Path('/root')
PROJECTS = pathlib.Path('/workspace/projects')
JOBS = pathlib.Path('/workspace/jobs')
CLAUDE = HOME / '.npm-global/bin/claude'
NAME = re.compile(r'^[a-z0-9][a-z0-9-]{0,40}$')
ALLOWED = ['Read', 'Edit', 'Write', 'Glob', 'Grep', 'Bash(npm test:*)', 'Bash(npm run test:*)', 'Bash(python3 -m pytest:*)']

RULES = """
RULES (from Felo, your manager):
- You are Felo Global's software engineer, backend AND frontend. Clients are professionals: write clean, secure, production-quality code.
- Frontend must look modern and polished like a high-performance company site: strong typography, generous spacing, responsive down
  to phone width, accessible (contrast, alt text, labels), no broken links, no lorem ipsum. Images: inline SVG or CSS, never hotlinked.
- Work only inside this folder. You can read, write and edit files and run the tests (npm test / pytest); nothing else.
- Write tests for logic you build and run them until they pass.
- Never deploy, push, send email, call payment services, or connect to any server. Never store secrets; use placeholders like
  process.env.NAME and list them in README.
- Keep a short README.md: what it is, how to run it, how to test it.
- Finish with a plain-English summary: what you built, test results, anything left or any decision Daniel must make."""


def out(*a): print(*a, flush=True)


def git(d, *a):
    return subprocess.run(['git', '-C', str(d), *a], capture_output=True, text=True)


def project(name):
    if not NAME.match(name or ''):
        sys.exit('Project name must be lowercase letters, numbers and dashes (e.g. oil-equipment-site).')
    d = PROJECTS / name
    d.mkdir(parents=True, exist_ok=True)
    if not (d / '.git').exists():
        git(d, 'init', '-q'); git(d, 'config', 'user.name', 'Felo'); git(d, 'config', 'user.email', 'felo@felo.invalid')
        git(d, 'commit', '-q', '--allow-empty', '-m', 'start ' + name)
    git(d, 'add', '-A'); git(d, 'commit', '-q', '-m', 'saved before new job')
    return d


def new_job(kind, proj, task):
    job = time.strftime('%Y%m%d-%H%M%S') + '-' + kind
    j = JOBS / job; j.mkdir(parents=True, exist_ok=True)
    (j / 'task.txt').write_text(task)
    meta = {'job': job, 'kind': kind, 'project': proj.name, 'status': 'running', 'started': time.strftime('%Y-%m-%d %H:%M:%S'),
            'before': git(proj, 'rev-parse', 'HEAD').stdout.strip()}
    (j / 'job.json').write_text(json.dumps(meta, indent=1))
    return j, meta


def finish(j, meta, proj, status, summary):
    git(proj, 'add', '-A')
    git(proj, 'commit', '-q', '-m', meta['job'] + ': ' + (j / 'task.txt').read_text()[:70])
    meta.update(status=status, finished=time.strftime('%Y-%m-%d %H:%M:%S'), after=git(proj, 'rev-parse', 'HEAD').stdout.strip())
    (j / 'job.json').write_text(json.dumps(meta, indent=1)); (j / 'summary.txt').write_text(summary)
    stat = git(proj, 'diff', '--stat', meta['before'], meta['after']).stdout.strip() or '(no files changed)'
    out(f"JOB {meta['job']} — {status.upper()}\nProject: {proj}\n\nSUMMARY:\n{summary}\n\nFILES CHANGED:\n{stat}\n\n"
        f"Next: check it with  python3 /root/.felo-team/felo-team.py review {proj.name}")


def build(name, task):
    if not CLAUDE.exists(): sys.exit('Claude Code is not installed in the workroom.')
    if not (HOME / '.claude/.credentials.json').exists(): sys.exit('Claude Code is not logged in yet. Tell Daniel.')
    env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN')}  # subscription only, never paid API
    proj = project(name); j, meta = new_job('build', proj, task)
    out(f"Started {meta['job']} (Claude Code, project {name}). This can take several minutes.")
    try:
        r = subprocess.run([str(CLAUDE), '-p', task + '\n' + RULES, '--model', 'opus', '--permission-mode', 'acceptEdits',
                            '--allowedTools', *ALLOWED, '--max-turns', '150', '--output-format', 'json'],
                           cwd=proj, env=env, capture_output=True, text=True, timeout=3600)
        (j / 'claude-output.json').write_text(r.stdout); (j / 'errors.txt').write_text(r.stderr[-20000:])
        try: res = json.loads(r.stdout)
        except ValueError: res = {'is_error': True, 'result': (r.stderr or r.stdout)[-1500:]}
        ok = r.returncode == 0 and not res.get('is_error')
        finish(j, meta, proj, 'done' if ok else 'failed', str(res.get('result') or '(no summary)')[:6000])
    except subprocess.TimeoutExpired:
        finish(j, meta, proj, 'failed', 'Stopped after 60 minutes. Partial work is saved in the commit; split the task smaller.')


def review(name):
    proj = PROJECTS / name
    if not (proj / '.git').exists(): sys.exit('No such project: ' + name)
    mine = sorted((json.loads(p.read_text()) for p in JOBS.glob('*/job.json')), key=lambda m: m['job'])
    mine = [m for m in mine if m['project'] == name]
    if mine:
        m = mine[-1]; out(f"Last job: {m['job']} — {m['status']}")
        if m.get('after'): out(git(proj, 'diff', '--stat', m['before'], m['after']).stdout)
    out('Project files:\n' + git(proj, 'ls-files').stdout[:4000])
    pkg = proj / 'package.json'
    if pkg.exists() and json.loads(pkg.read_text() or '{}').get('scripts', {}).get('test'):
        if not (proj / 'node_modules').exists(): subprocess.run(['npm', 'install', '--no-audit', '--no-fund'], cwd=proj, capture_output=True, timeout=600)
        r = subprocess.run(['npm', 'test'], cwd=proj, capture_output=True, text=True, timeout=900)
        out(f"TESTS (npm test): {'PASS' if r.returncode == 0 else 'FAIL'}\n" + (r.stdout + r.stderr)[-4000:])
    elif any(proj.glob('test*')) or any(proj.glob('tests/*.py')):
        r = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=proj, capture_output=True, text=True, timeout=900)
        out(f"TESTS (pytest): {'PASS' if r.returncode == 0 else 'FAIL'}\n" + (r.stdout + r.stderr)[-4000:])
    else:
        out('TESTS: none in this project. For a website, read the HTML/CSS yourself; ask for tests if it has logic.')
    out('Now read the changed files yourself before telling Daniel it is done.')


PREVIEW = 'https://felo-hermes.tail0ff06a.ts.net:8900/'


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.title = ''; self._in_title = False; self.meta = {}; self.lang = False
        self.h1 = 0; self.no_alt = 0; self.refs = []; self.hotlinked = 0; self.inputs = []; self.labels = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html' and a.get('lang'): self.lang = True
        if tag == 'title': self._in_title = True
        if tag == 'meta' and a.get('name'): self.meta[a['name'].lower()] = a.get('content') or ''
        if tag == 'h1': self.h1 += 1
        if tag == 'img':
            if a.get('alt') is None: self.no_alt += 1
            if re.match(r'https?://', a.get('src') or ''): self.hotlinked += 1
        if tag == 'label' and a.get('for'): self.labels.add(a['for'])
        if tag in ('input', 'textarea', 'select') and a.get('type') not in ('hidden', 'submit', 'button'):
            self.inputs.append((a.get('id'), a.get('aria-label') or a.get('aria-labelledby')))
        for k in ('href', 'src'):
            v = a.get(k)
            if v and not re.match(r'(https?:|mailto:|tel:|#|data:|javascript:|//)', v): self.refs.append(v.split('#')[0].split('?')[0])
    def handle_endtag(self, tag):
        if tag == 'title': self._in_title = False
    def handle_data(self, d):
        if self._in_title: self.title += d


def check_site(name):
    proj = PROJECTS / name
    if not proj.exists(): sys.exit('No such project: ' + name)
    pages = [p for p in proj.rglob('*.html') if not any(x.startswith('.') or x in ('node_modules', 'tests', 'test') for x in p.relative_to(proj).parts)]
    if not pages: sys.exit('No .html pages in ' + name)
    total = 0
    for p in sorted(pages):
        rel = p.relative_to(proj); text = p.read_text(errors='replace'); pg = Page(); pg.feed(text); issues = []
        if not pg.title.strip(): issues.append('no <title>')
        if not pg.meta.get('description'): issues.append('no meta description (Google snippet)')
        if 'viewport' not in pg.meta: issues.append('no mobile viewport tag')
        if not pg.lang: issues.append('<html> has no lang')
        if pg.h1 != 1: issues.append(f'{pg.h1} <h1> headings (should be exactly 1)')
        if pg.no_alt: issues.append(f'{pg.no_alt} image(s) without alt text')
        if pg.hotlinked: issues.append(f'{pg.hotlinked} image(s) loaded from other websites')
        for r in sorted(set(pg.refs)):
            t = (proj / r.lstrip('/')) if r.startswith('/') else (p.parent / r)
            if r and not (t.exists() or (t / 'index.html').exists()): issues.append('broken link/file: ' + r)
        unlabeled = [i for i, aria in pg.inputs if not aria and (not i or i not in pg.labels)]
        if unlabeled: issues.append(f'{len(unlabeled)} form field(s) without a label')
        low = text.lower()
        for w in ('lorem ipsum', 'your company', 'example.com', '555-'):
            if w in low: issues.append('placeholder text: "' + w + '"')
        for w in ('TODO', 'FIXME'):  # uppercase only: Spanish "todo" is a normal word
            if w in text: issues.append('unfinished marker: ' + w)
        total += len(issues)
        out(f"{rel}: " + ('OK' if not issues else '\n  - ' + '\n  - '.join(issues)))
    for p in proj.rglob('*'):
        if p.is_file() and '.git' not in p.parts and 'node_modules' not in p.parts and p.stat().st_size > 400_000:
            out(f"HEAVY FILE: {p.relative_to(proj)} ({p.stat().st_size // 1024} KB) — compress it"); total += 1
    out(f"\nRESULT: {'PASS' if total == 0 else str(total) + ' issue(s) to fix'}")
    out(f"Daniel can open the preview on his devices (Tailscale): {PREVIEW}{name}/")
    out('Also look yourself: design quality, wording, business facts. The checker cannot judge beauty.')



OLLAMA = 'http://100.109.89.77:11434/api/chat'
LOCAL_MODEL = 'gemma4:e4b'   # already loaded on the work PC for email reading: no model swapping
LOCAL_LIMIT = 24_000         # characters of input (about 6k tokens; context 8k)


def local(instruction, names):
    text = ''
    for n in names:
        p = pathlib.Path(n)
        if not p.is_file(): sys.exit('No such file: ' + n)
        text += f"\n\n=== {p.name} ===\n" + p.read_text(errors='replace')
    if not names and not sys.stdin.isatty(): text = sys.stdin.read()
    cut = len(text) > LOCAL_LIMIT
    body = {'model': LOCAL_MODEL, 'stream': False, 'think': False, 'options': {'num_ctx': 8192, 'temperature': 0.2},
            'messages': [{'role': 'system', 'content': 'You are a careful assistant. Follow the instruction using only the text given. Be concise. If the text does not contain the answer, say so.'},
                         {'role': 'user', 'content': instruction + ('\n\nTEXT:\n' + text[:LOCAL_LIMIT] if text else '')}]}
    try:
        req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as r: ans = json.load(r)['message']['content'].strip()
    except Exception:
        sys.exit('Local AI is offline (the work PC must be on). Do the job yourself only if it is small or urgent.')
    out(ans)
    if cut: out(f"\n[Note: only the first {LOCAL_LIMIT} characters were read; split long text into parts.]")


TEMPLATE = HOME / '.felo-team/proposal-template.html'


def proposal_start(name, code):
    if not re.fullmatch(r'[A-Z]{3}', code or ''): sys.exit('CODE must be 3 capital letters for the client, e.g. DGO for Dogo Group.')
    proj = project(name); d = proj / 'proposal'; d.mkdir(exist_ok=True); f = d / 'index.html'
    number = 'FGC-' + time.strftime('%Y-%m%d') + '-' + code
    if f.exists(): sys.exit(f'A proposal already exists: {f}. Edit it (keep its number) or move it to proposal/old-<date>.html first.')
    f.write_text(TEMPLATE.read_text().replace('{{FGC-YYYY-MMDD-XXX}}', number))
    out(f"Proposal {number} started: {f}\nFill every {{{{...}}}} (and delete sections that do not apply), then run:\n"
        f"  python3 /root/.felo-team/felo-team.py proposal-pdf {name}")


def proposal_pdf(name):
    d = PROJECTS / name / 'proposal'; f = d / 'index.html'
    if not f.exists(): sys.exit('No proposal yet. Start one with proposal-start.')
    html = f.read_text()
    left = sorted(set(m[:90] for m in re.findall(r'\{\{.*?\}\}', re.sub(r'<!--.*?-->', '', html, flags=re.S), flags=re.S)))
    if left: sys.exit('Not finished: these blanks are still in the proposal:\n  ' + '\n  '.join(left[:25]))
    ch = sorted(HOME.glob('.cache/ms-playwright/chromium-*/chrome-linux*/chrome'))
    if not ch: sys.exit('Chrome is not installed in the workroom (pip install playwright && playwright install chromium).')
    pdf = d / 'proposal.pdf'
    r = subprocess.run([str(ch[-1]), '--headless=new', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                        '--virtual-time-budget=3000', '--print-to-pdf=' + str(pdf), f.as_uri()], capture_output=True, text=True, timeout=120)
    if not pdf.exists() or pdf.stat().st_size < 2000:
        sys.exit('The PDF could not be made: ' + (r.stderr or r.stdout)[-400:])
    pages = len(re.findall(rb'/Type\s*/Page[^s]', pdf.read_bytes()))
    git(PROJECTS / name, 'add', '-A'); git(PROJECTS / name, 'commit', '-q', '-m', 'proposal PDF ' + time.strftime('%Y-%m-%d %H:%M'))
    out(f"PDF ready: {pdf} ({pages} page{'s' if pages != 1 else ''}, {pdf.stat().st_size // 1024} KB)\n"
        f"Daniel can open it (his devices): {PREVIEW}{name}/proposal/  and  {PREVIEW}{name}/proposal/proposal.pdf")


def jobs():
    for p in sorted(JOBS.glob('*/job.json'))[-15:]:
        m = json.loads(p.read_text()); out(f"{m['job']}  {m['project']:<24} {m['status']}")


def setup_check():
    ok = CLAUDE.exists() and (HOME / '.claude/.credentials.json').exists()
    out('Claude Code: ' + ('logged in' if ok else 'NOT logged in'))


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    PROJECTS.mkdir(parents=True, exist_ok=True); JOBS.mkdir(parents=True, exist_ok=True)
    cmd = a[0]
    if cmd == 'build' and len(a) == 3: build(a[1], a[2])
    elif cmd == 'review' and len(a) == 2: review(a[1])
    elif cmd == 'check-site' and len(a) == 2: check_site(a[1])
    elif cmd == 'local' and len(a) >= 2: local(a[1], a[2:])
    elif cmd == 'proposal-start' and len(a) == 3: proposal_start(a[1], a[2])
    elif cmd == 'proposal-pdf' and len(a) == 2: proposal_pdf(a[1])
    elif cmd == 'jobs': jobs()
    elif cmd == 'setup-check': setup_check()
    else: sys.exit(__doc__)
