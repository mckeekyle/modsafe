#!/usr/bin/env python3
"""Verify every curated mod link resolves to a published page. Nexus pages sit behind a browser
challenge, so Nexus mods are checked through Nexus Mods' public GraphQL API instead; other links via HTTP."""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "ModSafe/1.0 (+https://modsafe.app)", "Content-Type": "application/json"}


def nexus(pairs):
    out = {}
    for k in range(0, len(pairs), 15):
        ids = ",".join(f'{{gameDomain:"{d}",modId:{i}}}' for d, i in pairs[k:k + 15])
        q = "{ legacyModsByDomain(ids:[" + ids + "]) { nodes { modId name status updatedAt game { domainName } } } }"
        req = urllib.request.Request("https://api.nexusmods.com/v2/graphql", json.dumps({"query": q}).encode(), UA)
        for n in json.load(urllib.request.urlopen(req, timeout=30))["data"]["legacyModsByDomain"]["nodes"]:
            out[(n["game"]["domainName"], n["modId"])] = n
    return out


def http_ok(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]}, method="GET")
        return urllib.request.urlopen(req, timeout=30).status < 400
    except Exception:  # noqa: BLE001
        return False


def main():
    bad = 0
    for f in sorted((ROOT / "data/mods").glob("*.json")):
        d = json.loads(f.read_text())
        nx = nexus([(m["nexus_domain"], m["nexus_id"]) for m in d["mods"] if m["source"] == "nexus"])
        for m in d["mods"]:
            if m["source"] == "nexus":
                n = nx.get((m["nexus_domain"], m["nexus_id"]))
                ok = bool(n and n["status"] == "published")
                info = f"{n['name']} (updated {n['updatedAt'][:10]})" if n else "not found"
                if n:
                    m["last_updated"] = n["updatedAt"][:10]
            elif m["source"] == "modrinth":
                try:
                    pj = json.load(urllib.request.urlopen(urllib.request.Request(
                        f"https://api.modrinth.com/v2/project/{m['modrinth_slug']}", headers={"User-Agent": UA["User-Agent"]}), timeout=30))
                    ok, info = pj.get("status") == "approved", f"{pj['title']} (updated {pj['updated'][:10]})"
                    m["last_updated"] = pj["updated"][:10]
                except Exception as e:  # noqa: BLE001
                    ok, info = False, str(e)
            elif m["source"] == "thunderstore":
                try:
                    pj = json.load(urllib.request.urlopen(urllib.request.Request(
                        f"https://thunderstore.io/api/experimental/package/{m['thunderstore_package']}/", headers={"User-Agent": UA["User-Agent"]}), timeout=30))
                    ok = not pj.get("is_deprecated")
                    info = f"{pj['full_name']} {pj['latest']['version_number']} ({pj['latest']['date_created'][:10]})"
                    m["last_updated"] = pj["latest"]["date_created"][:10]
                except Exception as e:  # noqa: BLE001
                    ok, info = False, str(e)
            else:
                ok, info = http_ok(m["url"]), ""
            bad += not ok
            print(f"{'OK ' if ok else 'BAD'} {f.stem:16} {m['name'][:40]:40} {m['url']} {info}")
        if "--write" in sys.argv:
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print("all links verified" if not bad else f"{bad} problem link(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
