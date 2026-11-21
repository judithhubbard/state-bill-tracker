#!/usr/bin/env python3
"""The shared lists' backup (lists-backup.yml, daily): everything the state-lists Worker keeps in its KV namespace
(STATE_LISTS: lists with their edit keys, invite codes, view counts; not the daily rate counters), read with the admin
token from its /admin/export, a page at a time. The repository is public and a list's address and edit key are its only
protection, so the copy is kept only encrypted (the workflow encrypts it before uploading; nothing here prints a key,
an address or a list).

  python3 tools/lists_backup.py export lists.json      the whole namespace into lists.json (admin token from
                                                       LISTS_ADMIN_TOKEN, or else ~/.state_lists_admin)
  python3 tools/lists_backup.py restore lists.json DIR  wrangler's bulk files from a backup (DIR/kv-1.json ...), and the
                                                       commands that write them back; it writes nothing to the Worker

Restoring (the KV namespace lost or emptied, or a list deleted by mistake):
  1. Download the newest backup: gh run list --workflow lists-backup.yml, then
     gh run download <run id> -n shared-lists-<run id>   (gives lists.json.enc)
  2. Decrypt it with the passphrase (the LISTS_BACKUP_KEY secret; the owner's copy is ~/.state_lists_backup_key):
     openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in lists.json.enc -out lists.json -pass file:$HOME/.state_lists_backup_key
  3. If the namespace itself is gone: cd lists_worker && npx -y wrangler@4.152.0 kv namespace create STATE_LISTS, put the
     new id in lists_worker/wrangler.toml (binding LISTS), and deploy the Worker (npx -y wrangler@4.152.0 deploy). Never
     use the live NY site's LISTS namespace.
  4. python3 tools/lists_backup.py restore lists.json /tmp/kv  and run the commands it prints (from lists_worker/).
     KV's free plan allows 1,000 writes a day, so a backup of more keys is split into files of 900 to put on separate
     days (or turn on Workers Paid for the day). To bring back one list only, put just its "list:<slug>" key:
     npx -y wrangler@4.152.0 kv key put --binding LISTS --remote "list:<slug>" "<its JSON>"
  5. Delete lists.json and the bulk files afterwards: they hold every list's edit key.
"""
import json, os, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lists_admin  # noqa: E402  (call(): the admin requests, with the token)

CHUNK = 900


def export(out):
    keys, cursor, pages = {}, None, 0
    while True:
        page = lists_admin.call("GET", "/admin/export" + (f"?cursor={urllib.parse.quote(cursor)}" if cursor else ""))
        keys.update(page["keys"])
        pages += 1
        # (A Worker from before the export came in pages answers everything at once, with no cursor.)
        cursor = page.get("cursor")
        if not cursor:
            break
        if pages > 10000:
            raise SystemExit("export: too many pages")
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"exported": page.get("exported"), "keys": keys}, f, ensure_ascii=False)
    os.replace(tmp, out)
    kinds = {}
    for k in keys:
        kinds[k.split(":")[0]] = kinds.get(k.split(":")[0], 0) + 1
    print(f"{len(keys)} keys exported in {pages} page(s): " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
    if not any(k.startswith("code:") for k in keys) and keys:
        print("warning: no invite codes in the export")


def restore(src, folder):
    keys = json.load(open(src, encoding="utf-8"))["keys"]
    rows = [{"key": k, "value": json.dumps(v, ensure_ascii=False)} for k, v in sorted(keys.items()) if v is not None]
    os.makedirs(folder, exist_ok=True)
    files = []
    for i in range(0, len(rows), CHUNK):
        path = os.path.join(os.path.abspath(folder), f"kv-{i // CHUNK + 1}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows[i:i + CHUNK], f, ensure_ascii=False)
        files.append(path)
    print(f"{len(rows)} keys in {len(files)} file(s). From lists_worker/, one file a day on the free plan:")
    for path in files:
        print(f"  npx -y wrangler@4.152.0 kv bulk put --binding LISTS --remote {path}")
    print("Then delete them: they hold every list's edit key.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "export":
        export(a[1])
    elif len(a) == 3 and a[0] == "restore":
        restore(a[1], a[2])
    else:
        raise SystemExit(__doc__)
