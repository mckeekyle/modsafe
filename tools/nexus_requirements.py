#!/usr/bin/env python3
"""Compare each curated Nexus mod's `requires` with the requirements its author lists on Nexus
(public GraphQL API). --fix rewrites requires (install-order safe) and records other requirements."""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from games import GAMES_BY_SLUG  # noqa: E402

UA = {"User-Agent": "ModSafe/1.0 (+https://modsafe.app)", "Content-Type": "application/json"}


def fetch(domain, ids):
    out = {}
    for k in range(0, len(ids), 10):
        q = "{ legacyModsByDomain(ids:[" + ",".join(f'{{gameDomain:"{domain}",modId:{i}}}' for i in ids[k:k + 10]) + \
            "]) { nodes { modId name modRequirements { nexusRequirements { nodes { modId modName externalRequirement url } } } } } }"
        req = urllib.request.Request("https://api.nexusmods.com/v2/graphql", json.dumps({"query": q}).encode(), UA)
        for n in json.load(urllib.request.urlopen(req, timeout=30))["data"]["legacyModsByDomain"]["nodes"]:
            out[n["modId"]] = n["modRequirements"]["nexusRequirements"]["nodes"]
    return out


def main(fix=False):
    for f in sorted((ROOT / "data/mods").glob("*.json")):
        d = json.loads(f.read_text())
        nxm = [m for m in d["mods"] if m["source"] == "nexus"]
        if not nxm:
            continue
        dom = nxm[0]["nexus_domain"]
        by_nexus = {m["nexus_id"]: m["id"] for m in nxm}
        for fw in GAMES_BY_SLUG[d["game"]]["frameworks"]:
            mm = re.search(r"nexusmods\.com/\w+/mods/(\d+)", fw.get("url", ""))
            if mm:
                by_nexus.setdefault(int(mm.group(1)), fw["id"])
        reqs = fetch(dom, [m["nexus_id"] for m in nxm])
        order = [m["id"] for m in d["mods"]]
        fw_ids = {fw["id"] for fw in GAMES_BY_SLUG[d["game"]]["frameworks"]}
        for m in nxm:
            nodes = reqs.get(m["nexus_id"], [])
            mapped, other = [], []
            for n in nodes:
                rid = by_nexus.get(int(n["modId"])) if n.get("modId") and not n.get("externalRequirement") else None
                if rid and rid != m["id"]:
                    mapped.append(rid)
                else:
                    other.append(n["modName"])
            have = set(m["requires"])
            miss, extra = set(mapped) - have, have - set(mapped)
            if miss or extra or other:
                print(f"{f.stem:15} {m['name'][:34]:34} missing={sorted(miss)} extra={sorted(extra)} other={other}")
            if fix:
                idx = order.index(m["id"])
                ok = [r for r in mapped if r in fw_ids or r in order[:idx]]
                m["requires"] = list(dict.fromkeys(ok))
                late = [r for r in mapped if r not in ok]
                m["also_requires"] = list(dict.fromkeys(other + [r for r in late]))
                if not m["also_requires"]:
                    m.pop("also_requires")
        if fix:
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main("--fix" in sys.argv)
