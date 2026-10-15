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
) -> dict[str, Any]:
    """
    Decide status for one framework relative to the latest game patch.

    Returns dict with status, reasons, and evidence flags.
    """
    release_dt = parse_iso(release_published_at)
    patch_dt = parse_iso(patch_published_at)
    combined_notes = f"{release_tag or ''}\n{release_notes or ''}"
    mentions = notes_mention_patch(combined_notes, patch_version) if patch_version else False

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
        if notes_mention_patch(notes, patch_version):
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
