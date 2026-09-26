#!/bin/bash
# Check a Nextcloud app password with a read-only WebDAV request. Never prints it.
R=/root/felo-v2-runtime; umask 077
U=$(sed -n 's/^NEXTCLOUD_USER=//p' $R/app.run.env); URL=$(sed -n 's/^NEXTCLOUD_URL=//p' $R/app.run.env)
probe(){ printf 'user = "%s:%s"\n' "$U" "$(cat $1)" > $R/pending/.curlcfg
  curl -s -o /dev/null -w '%{http_code}' --max-time 15 -K $R/pending/.curlcfg -X PROPFIND -H 'Depth: 0' "$URL/remote.php/dav/files/$U/"; rm -f $R/pending/.curlcfg; }
sed -n 's/^NEXTCLOUD_PASS=//p' $R/app.run.env | tr -d '\n' > $R/pending/.cur
echo "new password: HTTP $(probe $R/pending/nextcloud)  (207 = works, 401 = rejected)"
echo "current (old) password: HTTP $(probe $R/pending/.cur)"
echo "new password length: $(wc -c < $R/pending/nextcloud) characters"
shred -u $R/pending/.cur
