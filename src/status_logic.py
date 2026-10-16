"""
Status determination for Cyberpunk 2077 core framework mod compatibility.

Statuses (honest, evidence-based):
- 'Updated for latest patch': release notes explicitly mention the current patch version
- 'Likely OK': latest release is newer than the patch date, but notes do not name the patch
- 'Unknown / check': release is older than the patch, or evidence is insufficient
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional


STATUS_UPDATED = "Updated for latest patch"
STATUS_LIKELY = "Likely OK"
STATUS_UNKNOWN = "Unknown / check"

# Official CDPR Steam community announcements that look like patch drops.
PATCH_TITLE_RE = re.compile(
    r"(?i)^(?:patch|update)\s+(\d+\.\d+(?:\.\d+)?)\b"
    r"|^(?:edgerunners update\s*\(patch\s+(\d+\.\d+(?:\.\d+)?)\))"
)

# Match a game version mentioned in release notes (e.g. "2.31", "patch 2.3").
def patch_mention_pattern(version: str) -> re.Pattern[str]:
    # Escape dots; allow optional "patch "/"update " prefix; word boundaries.
    esc = re.escape(version)
    return re.compile(
        rf"(?i)(?:(?:patch|update|game(?:\s+version)?|for)\s+)?\b{esc}\b"
    )


def parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    # GitHub uses Z; Steam unix handled elsewhere.
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def extract_patch_version_from_title(title: str) -> Optional[str]:
    """Return version string from an official patch announcement title, or None."""
    if not title:
        return None
    m = PATCH_TITLE_RE.match(title.strip())
    if not m:
        # Also accept "Update 2.2 is live!" style
        m2 = re.search(r"(?i)\b(?:patch|update)\s+(\d+\.\d+(?:\.\d+)?)\b", title)
        if m2 and not re.search(r"(?i)\b(coming|revealed|tomorrow|notes)\b", title):
            # "Update 2.1 Patch Notes" / "coming" are pre-announcements — still useful
            # for version identity, but for "latest live patch" we prefer live titles.
            return m2.group(1)
        if m2:
            return m2.group(1)
        return None
    return m.group(1) or m.group(2)


def is_live_patch_announcement(title: str) -> bool:
    """True if the title looks like a patch that is live / released, not a teaser."""
    t = title.lower()
    if re.search(r"\b(coming|revealed|tomorrow|development update|insight)\b", t):
        return False
    if re.search(r"\b(list of changes|patch notes)\b", t) and "is live" not in t and "is now" not in t:
        # Pre-release notes posts — still count as identifying a version if same day,
        # but prefer "is live" / "Patch X.Y" alone.
        if re.match(r"(?i)^(patch|update)\s+\d+", title.strip()):
            return True
        return False
    return bool(re.search(r"(?i)\b(patch|update)\s+\d+\.\d+", title))


def select_latest_game_patch(news_items: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """
    From Steam news items (preferably steam_community_announcements), pick the
    most recent live patch announcement.
    """
    candidates: list[dict[str, Any]] = []
    for item in news_items:
        title = item.get("title") or ""
        version = extract_patch_version_from_title(title)
        if not version:
            continue
        if not is_live_patch_announcement(title):
            continue
        date_unix = item.get("date")
        if date_unix is None:
            continue
        published = datetime.fromtimestamp(int(date_unix), tz=timezone.utc)
        candidates.append(
            {
                "version": version,
                "title": title,
                "published_at": published.isoformat().replace("+00:00", "Z"),
                "published_unix": int(date_unix),
                "url": item.get("url") or "",
                "gid": item.get("gid") or "",
                "summary": (item.get("contents") or "")[:500],
            }
        )

    if not candidates:
        return None

    # Prefer higher semantic version when dates are close; primarily sort by date.
    def version_key(v: str) -> tuple:
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    candidates.sort(key=lambda c: (c["published_unix"], version_key(c["version"])), reverse=True)
    return candidates[0]


def list_game_patches(news_items: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    """Unique patch versions from news, newest first."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    # Collect then sort
    raw: list[dict[str, Any]] = []
    for item in news_items:
        title = item.get("title") or ""
        version = extract_patch_version_from_title(title)
        if not version or not is_live_patch_announcement(title):
            continue
        date_unix = item.get("date")
        if date_unix is None:
            continue
        published = datetime.fromtimestamp(int(date_unix), tz=timezone.utc)
        raw.append(
            {
                "version": version,
                "title": title,
                "published_at": published.isoformat().replace("+00:00", "Z"),
                "published_unix": int(date_unix),
                "url": item.get("url") or "",
            }
        )
    raw.sort(key=lambda c: c["published_unix"], reverse=True)
    for c in raw:
        if c["version"] in seen:
            continue
        seen.add(c["version"])
        out.append(c)
        if len(out) >= limit:
            break
    return out


def notes_mention_patch(notes: str, patch_version: str) -> bool:
    """True if release body/name clearly references this patch version."""
    if not notes or not patch_version:
        return False
    # Prefer explicit "patch 2.31" / "support for 2.31" style; bare version match
    # is allowed but we require nearby support/patch context when version is short.
    text = notes
    pat = patch_mention_pattern(patch_version)
    if not pat.search(text):
        # Try parent version: notes may say "2.3" when patch is "2.31" only if
        # we are checking exact — do NOT fuzzy-match 2.3 for 2.31.
        return False
    # Extra honesty: require that a match for a minor like "2.3" isn't only
    # matching inside "2.31". The word-boundary pattern already handles that
    # for \b2\.3\b vs 2.31.
    return True


def pick_latest_stable_release(releases: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Prefer the newest non-prerelease; fall back to newest including prereleases."""
    stables = [r for r in releases if not r.get("prerelease") and not r.get("draft")]
    pool = stables if stables else [r for r in releases if not r.get("draft")]
    if not pool:
        return None

    def key(r: dict[str, Any]) -> datetime:
        return parse_iso(r.get("published_at")) or datetime.fromtimestamp(0, tz=timezone.utc)

    pool = sorted(pool, key=key, reverse=True)
    return pool[0]


def determine_framework_status(
    *,
    release_published_at: Optional[str],
    release_notes: str,
    release_tag: str,
    patch_version: str,
    patch_published_at: str,
    mention_fn=None,
) -> dict[str, Any]:
    """
    Decide status for one framework relative to the latest game patch.

    Returns dict with status, reasons, and evidence flags.
    """
    release_dt = parse_iso(release_published_at)
    patch_dt = parse_iso(patch_published_at)
    combined_notes = f"{release_tag or ''}\n{release_notes or ''}"
    if mention_fn is not None:
        mentions = bool(mention_fn(combined_notes))
    else:
        mentions = notes_mention_patch(combined_notes, patch_version) if patch_version else False
    patch_version = patch_version or "(unnumbered)"

    newer_than_patch = False
    if release_dt and patch_dt:
        newer_than_patch = release_dt >= patch_dt

    if mentions and newer_than_patch:
        status = STATUS_UPDATED
        reason = (
            f"Latest release notes mention patch {patch_version} "
            f"and the release is on/after the patch date."
        )
    elif mentions and not newer_than_patch:
        # Unusual: notes mention patch but dated earlier (scheduled/wrong clock) —
        # still treat as updated if explicit mention exists.
        status = STATUS_UPDATED
        reason = (
            f"Release notes mention patch {patch_version}, "
            f"even though the release timestamp is before the patch announcement."
        )
    elif newer_than_patch:
        status = STATUS_LIKELY
        reason = (
            f"Latest release is newer than patch {patch_version}, "
            f"but notes do not explicitly mention that version."
        )
    else:
        status = STATUS_UNKNOWN
        if release_dt and patch_dt:
            reason = (
                f"Latest release predates patch {patch_version}; "
                f"compatibility is unverified — check the project page."
            )
        else:
            reason = "Insufficient date or version evidence to assess compatibility."

    return {
        "status": status,
        "reason": reason,
        "mentions_patch": mentions,
        "newer_than_patch": newer_than_patch,
    }


def status_for_patch_history(
    *,
    releases: list[dict[str, Any]],
    patch_version: str,
    patch_published_at: str,
    mention_fn=None,
) -> dict[str, Any]:
    """
    For a historical patch, find the best matching release evidence:
    prefer a release that mentions the patch; else the first release on/after the patch.
    """
    patch_dt = parse_iso(patch_published_at)
    mentioned = []
    after = []
    for r in releases:
        if r.get("draft"):
            continue
        tag = r.get("tag_name") or ""
        body = r.get("body") or ""
        pub = r.get("published_at")
        notes = f"{tag}\n{body}"
        hit = mention_fn(notes) if mention_fn is not None else notes_mention_patch(notes, patch_version)
        if hit:
            mentioned.append(r)
        rdt = parse_iso(pub)
        if patch_dt and rdt and rdt >= patch_dt and not r.get("prerelease"):
            after.append(r)

    if mentioned:
        # Newest mention
        mentioned.sort(
            key=lambda r: parse_iso(r.get("published_at"))
            or datetime.fromtimestamp(0, tz=timezone.utc),
            reverse=True,
        )
        r = mentioned[0]
        return {
            "status": STATUS_UPDATED,
            "release_tag": r.get("tag_name"),
            "release_published_at": r.get("published_at"),
            "mentions_patch": True,
        }

    if after:
        after.sort(
            key=lambda r: parse_iso(r.get("published_at"))
            or datetime.fromtimestamp(0, tz=timezone.utc),
        )
        r = after[0]  # earliest after patch
        return {
            "status": STATUS_LIKELY,
            "release_tag": r.get("tag_name"),
            "release_published_at": r.get("published_at"),
            "mentions_patch": False,
        }

    return {
        "status": STATUS_UNKNOWN,
        "release_tag": None,
        "release_published_at": None,
        "mentions_patch": False,
    }


FRAMEWORKS = [
    {
        "id": "cet",
        "name": "Cyber Engine Tweaks",
        "short": "CET",
        "repo": "maximegmd/CyberEngineTweaks",
        "url": "https://github.com/maximegmd/CyberEngineTweaks",
    },
    {
        "id": "red4ext",
        "name": "RED4ext",
        "short": "RED4ext",
        "repo": "WopsS/RED4ext",
        "url": "https://github.com/WopsS/RED4ext",
    },
    {
        "id": "redscript",
        "name": "redscript",
        "short": "redscript",
        "repo": "jac3km4/redscript",
        "url": "https://github.com/jac3km4/redscript",
    },
    {
        "id": "archive-xl",
        "name": "ArchiveXL",
        "short": "ArchiveXL",
        "repo": "psiberx/cp2077-archive-xl",
        "url": "https://github.com/psiberx/cp2077-archive-xl",
    },
    {
        "id": "tweak-xl",
        "name": "TweakXL",
        "short": "TweakXL",
        "repo": "psiberx/cp2077-tweak-xl",
        "url": "https://github.com/psiberx/cp2077-tweak-xl",
    },
    {
        "id": "codeware",
        "name": "Codeware",
        "short": "Codeware",
        "repo": "psiberx/cp2077-codeware",
        "url": "https://github.com/psiberx/cp2077-codeware",
    },
]


def determine_with_lineage(
    *,
    release_published_at: Optional[str],
    release_notes: str,
    release_tag: str,
    patch_version: str,
    patch_published_at: str,
    lineage_mention_tags: list[str],
    mention_fn=None,
) -> dict[str, Any]:
    """
    Like determine_framework_status, but if the latest notes omit the version while
    a post-patch release in the same project declared support, treat as Updated
    when the latest release is still on/after the patch.
    """
    base = determine_framework_status(
        release_published_at=release_published_at,
        release_notes=release_notes,
        release_tag=release_tag,
        patch_version=patch_version,
        patch_published_at=patch_published_at,
        mention_fn=mention_fn,
    )
    if base["status"] == STATUS_UPDATED:
        return base
    if base["newer_than_patch"] and lineage_mention_tags:
        return {
            "status": STATUS_UPDATED,
            "reason": (
                f"Latest release is on/after patch {patch_version}; "
                f"an earlier post-patch release ({', '.join(lineage_mention_tags)}) "
                f"explicitly mentioned that version."
            ),
            "mentions_patch": True,
            "newer_than_patch": True,
        }
    return base


# ---------------------------------------------------------------------------
# Multi-game helpers
# ---------------------------------------------------------------------------

def detect_patch(title: str, rule: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Generic Steam-announcement patch detector driven by a per-game rule:
      include: regex the title must match
      exclude: regex that disqualifies the title (teasers, betas, CK updates…)
      version: regex whose group(1) is the version (optional)
      label:   format string for display, using {v} (version) or {date}
    Returns {"version": str|None, "label_hint": str} or None.
    """
    if not title:
        return None
    t = title.strip()
    if rule.get("exclude") and re.search(rule["exclude"], t, re.I):
        return None
    if not re.search(rule["include"], t, re.I):
        return None
    version = None
    if rule.get("version"):
        m = re.search(rule["version"], t, re.I)
        if m:
            version = m.group(1)
    if rule.get("require_version") and not version:
        return None
    return {"version": version}


def notes_cover_version(notes: str, version: Optional[str], series_depth: Optional[int] = None) -> bool:
    """
    True when notes explicitly declare a version range that contains `version`:
      - wildcard ranges such as "v1.4.x" / "1.x" (any game), e.g. BLSE "For v1.0.x/.../v1.4.x" covers 1.4.8;
      - for games whose mod compatibility is declared per release series (series_depth, e.g. RimWorld's
        About.xml supportedVersions use major.minor), an explicit "RimWorld 1.6" / "update to 1.6" covers
        build 1.6.4850. Bare numbers without that context never count.
    """
    if not notes or not version or not re.fullmatch(r"\d+(?:\.\d+)+", version):
        return False
    parts = version.split(".")
    for i in range(1, len(parts)):
        pre = r"\.".join(map(re.escape, parts[:i]))
        if re.search(rf"(?<![\w.])v?{pre}\.[x*](?![\w.])", notes, re.I):
            return True
    if series_depth and len(parts) > series_depth:
        series = r"\.".join(map(re.escape, parts[:series_depth]))
        ctx = r"(?:rimworld|update(?:d)?\s+(?:to|for)|support(?:s|ed)?(?:\s+for)?|compatible\s+with|for)"
        if re.search(rf"(?i)\b{ctx}\s+v?{series}(?![\w.]|\.\d)", notes):
            return True
    return False


def make_mention_fn(version: Optional[str], template: Optional[str], series_depth: Optional[int] = None):
    """Build a notes->bool matcher for a patch version (None => never matches)."""
    if not version:
        return lambda _notes: False
    if template:
        rx = re.compile(template.format(v=re.escape(version)), re.I)
        base = lambda notes: bool(rx.search(notes or ""))
    else:
        base = lambda notes: notes_mention_patch(notes or "", version)
    return lambda notes: base(notes) or notes_cover_version(notes or "", version, series_depth)


def list_patches_generic(news_items: list[dict[str, Any]], rule: dict[str, Any], limit: int = 15) -> list[dict[str, Any]]:
    """Patch announcements newest first, de-duplicated by version/label."""
    raw = []
    for item in news_items:
        title = item.get("title") or ""
        d = detect_patch(title, rule)
        if not d or item.get("date") is None:
            continue
        published = datetime.fromtimestamp(int(item["date"]), tz=timezone.utc)
        date_s = published.strftime("%Y-%m-%d")
        v = d["version"]
        if v:
            label = (rule.get("label") or "{v}").format(v=v, date=date_s, title=title)
        else:
            label = (rule.get("label_noversion") or "{date}").format(date=date_s, title=title)
        raw.append(
            {
                "version": v,
                "label": label.strip(),
                "title": title,
                "published_at": published.isoformat().replace("+00:00", "Z"),
                "published_unix": int(item["date"]),
                "url": item.get("url") or "",
            }
        )
    raw.sort(key=lambda c: c["published_unix"], reverse=True)
    seen: set[str] = set()
    out = []
    for c in raw:
        key = c["label"]
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= limit:
            break
    return out


def overall_verdict(statuses: list[str]) -> str:
    """Game-level verdict = the weakest status among auto-tracked frameworks."""
    if not statuses:
        return STATUS_UNKNOWN
    if any(s == STATUS_UNKNOWN for s in statuses):
        return STATUS_UNKNOWN
    if any(s == STATUS_LIKELY for s in statuses):
        return STATUS_LIKELY
    return STATUS_UPDATED


# --- Minecraft -------------------------------------------------------------

def neoforge_versions_for(mc_version: str, versions: list[str]) -> list[str]:
    """
    NeoForge versions targeting a Minecraft release.
    Old scheme: MC 1.21.4 -> 21.4.x, MC 1.21 -> 21.0.x.
    New scheme (MC 26.x): MC 26.3 -> 26.3.0.x, MC 26.1.2 -> 26.1.2.x.
    """
    parts = mc_version.split(".")
    if parts[0] == "1" and len(parts) >= 2:
        minor = parts[1]
        patch = parts[2] if len(parts) > 2 else "0"
        prefix = f"{minor}.{patch}."
        return [v for v in versions if v.startswith(prefix)]
    if len(parts) == 2:
        prefixes = (f"{mc_version}.0.",)
    else:
        prefixes = (f"{mc_version}.",)
    return [v for v in versions if v.startswith(prefixes)]


def loader_support_status(*, has_stable: bool, has_any: bool, what: str, mc_version: str) -> dict[str, str]:
    """Map 'a build exists for this MC version' evidence to the honest statuses."""
    if has_stable:
        return {"status": STATUS_UPDATED, "reason": f"{what} publishes a stable build for Minecraft {mc_version}."}
    if has_any:
        return {
            "status": STATUS_LIKELY,
            "reason": f"{what} has only beta/latest (not recommended/stable) builds for Minecraft {mc_version}.",
        }
    return {"status": STATUS_UNKNOWN, "reason": f"No {what} build found for Minecraft {mc_version} yet."}


# ---------------------------------------------------------------------------
# User-facing verdicts (v3): friendlier labels, patch-sensitivity, time signal
# ---------------------------------------------------------------------------

V_SAFE = "Safe"
V_LIKELY = "Likely safe"
V_WAIT = "Just patched, wait"
V_BROKEN = "Breakage reported"
V_NOT_PORTED = "Not ported yet"
V_NODATA = "No data"
V_AGNOSTIC = "Not affected by patches"
V_MANUAL = "Check manually"

# Lower = worse. Only these participate in the game verdict.
VERDICT_RANK = {V_BROKEN: 0, V_NOT_PORTED: 1, V_WAIT: 2, V_NODATA: 3, V_LIKELY: 4, V_SAFE: 5}

FRESH_PATCH_DAYS = 7

BREAK_WORD_RE = re.compile(
    r"(?i)\b(crash\w*|broken|breaks?|not working|doesn'?t work|does not work|won'?t (?:load|launch|start)|"
    r"fails? to (?:load|launch|start)|incompatib\w*|not compatible|stopped working)\b"
)
PATCH_WORD_RE = re.compile(r"(?i)\b(patch|update[ds]?|hotfix|new version|game version|latest version|runtime)\b")


def is_breakage_title(title: str, patch_version: Optional[str] = None) -> bool:
    """Issue title reports breakage *tied to a game update* (both signals required)."""
    if not title or not BREAK_WORD_RE.search(title):
        return False
    if PATCH_WORD_RE.search(title):
        return True
    if patch_version and re.search(rf"(?<![\w.]){re.escape(patch_version)}(?![\w])", title, re.I):
        return True
    return False


def patch_age_days(patch_published_at: str, now: Optional[datetime] = None) -> float:
    dt = parse_iso(patch_published_at)
    if not dt:
        return 0.0
    now = now or datetime.now(timezone.utc)
    return (now - dt).total_seconds() / 86400


CONFIRM_LABEL_RE = re.compile(r"(?i)\b(bug|confirmed|regression|crash|broken|critical)\b")


def confirmed_breakage(reports: list[dict]) -> list[dict]:
    """A lone, unlabeled issue from one user is a lead, not evidence. Treat reports as confirmed when a
    maintainer labeled one as a bug/regression, others +1'd it, or several independent reports exist."""
    if not reports:
        return []
    if len(reports) >= 2:
        return reports
    return [r for r in reports if any(CONFIRM_LABEL_RE.search(l) for l in r.get("labels", []))
            or r.get("thumbs_up", 0) >= 2]


def user_verdict(
    *,
    base_status: Optional[str],
    age_days: float,
    sensitive: bool = True,
    breakage: Optional[list] = None,
    official_support: bool = False,
    has_error: bool = False,
    absence_is_definitive: bool = False,
) -> str:
    """
    Map evidence to a user-facing label.
      base_status: STATUS_UPDATED / STATUS_LIKELY / STATUS_UNKNOWN from release evidence
      breakage: open issues reporting update breakage filed since the patch (after latest release)
      official_support: maintainer's official page lists support for the current runtime
      absence_is_definitive: (Minecraft) no build for this version means it's genuinely unsupported
    """
    if not sensitive:
        return V_AGNOSTIC
    if has_error or base_status is None:
        return V_NODATA
    if base_status == STATUS_UPDATED or official_support:
        return V_SAFE
    if breakage:
        return V_BROKEN
    if base_status == STATUS_LIKELY:
        return V_LIKELY
    # No release since the patch.
    if age_days < FRESH_PATCH_DAYS:
        return V_WAIT
    if absence_is_definitive:
        return V_NOT_PORTED
    return V_LIKELY


def game_verdict(labels: list[str]) -> str:
    ranked = [l for l in labels if l in VERDICT_RANK]
    if not ranked:
        return V_NODATA
    return min(ranked, key=lambda l: VERDICT_RANK[l])


def history_label(base_status: str) -> str:
    return {STATUS_UPDATED: V_SAFE, STATUS_LIKELY: V_LIKELY}.get(base_status, "No post-patch release")


SILVERLOCK_RE = [
    # F4SE: "Fallout 4 runtime 1.11.240 - build: 0.7.9"
    re.compile(r"runtime\s+(\d+(?:\.\d+)+)\s*-\s*build:?\s*(\d+(?:\.\d+)+)", re.I),
    # SKSE: "build 2.3.1 (game version 1.7.104)"
    re.compile(r"build\s+(\d+(?:\.\d+)+)\s*\(game version\s+(\d+(?:\.\d+)+)\)", re.I),
]


def parse_silverlock(text: str) -> Optional[dict[str, str]]:
    """First (current) runtime/build pair on an ianpatt silverlock.org page."""
    best = None
    for i, rx in enumerate(SILVERLOCK_RE):
        m = rx.search(text or "")
        if m and (best is None or m.start() < best[0]):
            runtime, build = (m.group(1), m.group(2)) if i == 0 else (m.group(2), m.group(1))
            best = (m.start(), {"runtime": runtime, "build": build})
    return best[1] if best else None


MANUAL_STALE_DAYS = 14


def manual_hook_verdict(*, supported: list[str], current: list[str], patch_age: float, verified_age: float) -> dict[str, str]:
    """Verdict for a hand-maintained 'supported builds' record (e.g. Script Hook V)."""
    missing = [b for b in current if b not in supported]
    if not missing:
        if verified_age > MANUAL_STALE_DAYS:
            return {"status": V_LIKELY, "reason": f"Supported builds matched the game when last checked, but that was {int(verified_age)} days ago."}
        return {"status": V_SAFE, "reason": "Supports the current game build(s): " + ", ".join(current) + "."}
    if patch_age < FRESH_PATCH_DAYS:
        return {"status": V_WAIT, "reason": "No build yet for " + ", ".join(missing) + "; the update is under a week old."}
    return {"status": V_NOT_PORTED, "reason": "No build yet for " + ", ".join(missing) + "."}


def merge_silent_patches(patches: list[dict[str, Any]], silent: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Add hand-maintained, sourced updates that shipped without a Steam announcement (hotfixes posted on Discord,
    or mentioned only in later dev posts). Only entries with a valid date are inserted, a label
    already present is never duplicated, and the result stays newest-first.
    """
    have = {p["label"] for p in patches}
    out = list(patches)
    for sp in silent or []:
        dt = parse_iso(sp.get("published_at"))
        if not dt or sp.get("label") in have:
            continue
        out.append({"version": sp.get("version"), "label": sp["label"], "title": sp.get("title") or sp["label"],
                    "published_at": dt.isoformat().replace("+00:00", "Z"), "published_unix": int(dt.timestamp()),
                    "url": sp.get("url") or "", "silent": True, "sources": sp.get("sources", [])})
    out.sort(key=lambda c: c["published_unix"], reverse=True)
    return out


def same_release_line(tag: Optional[str], latest_tag: Optional[str]) -> bool:
    """True unless both tags have numeric versions with different major numbers (a separate maintenance branch)."""
    def major(t):
        m = re.search(r"(\d+)(?:\.\d+)", t or "")
        return int(m.group(1)) if m else None
    a, b = major(tag), major(latest_tag)
    return a is None or b is None or a == b


UNANNOUNCED_DEDUPE_DAYS = 2


def parse_steam_public_build(info: dict, appid) -> Optional[dict[str, Any]]:
    """Public-branch build from api.steamcmd.net/v1/info/<appid> (Steam PICS). None if absent/malformed."""
    try:
        if info.get("status") != "success":
            return None
        b = info["data"][str(appid)]["depots"]["branches"]["public"]
        ts = int(b["timeupdated"])
    except (KeyError, TypeError, ValueError):
        return None
    if ts <= 0:
        return None
    return {"buildid": str(b.get("buildid") or ""), "timeupdated": ts,
            "published_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")}


def detect_unannounced_update(build: Optional[dict], patches: list[dict[str, Any]],
                              dedupe_days: float = UNANNOUNCED_DEDUPE_DAYS) -> Optional[dict[str, Any]]:
    """
    A Steam public build newer than the latest tracked patch, with no tracked patch (news or sourced silent patch)
    within `dedupe_days` of it, is an 'unannounced update'. It never carries a version number.
    """
    if not build or not patches:
        return None
    bdt = datetime.fromtimestamp(build["timeupdated"], tz=timezone.utc)
    latest = max(parse_iso(p.get("published_at")) or datetime.fromtimestamp(0, tz=timezone.utc) for p in patches)
    if (bdt - latest).total_seconds() <= dedupe_days * 86400:
        return None
    for p in patches:
        pdt = parse_iso(p.get("published_at"))
        if pdt and abs((bdt - pdt).total_seconds()) <= dedupe_days * 86400:
            return None
    return {"version": None, "label": f"Unannounced update {bdt:%Y-%m-%d}", "published_at": build["published_at"],
            "buildid": build.get("buildid"), "source": "Steam public branch (api.steamcmd.net / PICS)"}


def apply_unannounced(label: str, reason: str, *, sensitive: bool, release_published_at: Optional[str],
                      event: Optional[dict], now: Optional[datetime] = None) -> tuple[str, str]:
    """
    Conservative handling: a fresh unannounced build (< FRESH_PATCH_DAYS) puts patch-sensitive tools without a
    newer release on 'Just patched, wait'; an older one keeps the verdict (no breakage signal) but flags a recheck.
    """
    if not event or not sensitive or label in (V_BROKEN, V_NOT_PORTED, V_NODATA, V_AGNOSTIC, V_MANUAL):
        return label, reason
    edt = parse_iso(event["published_at"])
    rdt = parse_iso(release_published_at)
    if not edt or (rdt and rdt >= edt):
        return label, reason
    day = edt.strftime("%Y-%m-%d")
    if patch_age_days(event["published_at"], now) < FRESH_PATCH_DAYS:
        return V_WAIT, reason + (f" Steam's public build changed on {day} (build {event.get('buildid')}) with no "
                                 "announcement, and this tool hasn't released since; wait for confirmation.")
    return label, reason + (f" Note: Steam's public build changed on {day} (build {event.get('buildid')}) without an "
                            "announcement; this status reflects the last announced patch, so recheck if you hit problems.")
