#!/usr/bin/env python3
"""Check every blob in every ref of a bare repo for Felo's current secret values. Prints counts only."""
import re, subprocess, sys, hashlib
vals = set()
for f in ["/root/felo-v2-runtime/app.run.env", "/root/felo-v2-runtime/intake.env", "/root/felo-v2-runtime/ntfy.env"]:
    for line in open(f):
        if "=" in line:
            k, v = line.rstrip("\n").split("=", 1)
            # passwords, tokens, keys, topics and URLs that embed credentials
            if len(v) >= 12 and re.search(r"PASS|SECRET|TOKEN|KEY|TOPIC|DATABASE_URL", k):
                vals.add(v)
                m = re.match(r"\w+://[^:/]+:([^@]+)@", v)
                if m: vals.add(m.group(1))
pat = [re.compile(re.escape(v).encode()) for v in vals]
for repo in sys.argv[1:]:
    objs = subprocess.run(["git", "--git-dir", repo, "rev-list", "--objects", "--all"], capture_output=True, text=True).stdout.split("\n")
    shas = [o.split(" ")[0] for o in objs if o]
    hits = 0; blobs = 0
    batch = subprocess.run(["git", "--git-dir", repo, "cat-file", "--batch"], input=("\n".join(shas) + "\n").encode(), capture_output=True).stdout
    i = 0
    while i < len(batch):
        nl = batch.index(b"\n", i); head = batch[i:nl].split()
        if len(head) < 3: break
        size = int(head[2]); body = batch[nl + 1: nl + 1 + size]; i = nl + 1 + size + 1
        if head[1] == b"blob":
            blobs += 1
            if any(p.search(body) for p in pat): hits += 1
    print(f"{repo}: {blobs} file versions checked against {len(vals)} current secrets -> {hits} containing a secret")
