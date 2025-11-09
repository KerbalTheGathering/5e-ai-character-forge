import httpx
from requests_cache import CachedSession
from .schemas import CharacterDraft, BackstoryResult, ProgressionPlan, Proficiency
from .config import RULES_BASE, RULES_API_PREFIX, cache_dir
from typing import List

# Rules cache
rules_cache = CachedSession(cache_name=str(cache_dir / "rules_cache"), backend="sqlite", expire_after=60*60*24)

def mod(score: int) -> int:
    return (score - 10) // 2

def pb(level: int) -> int:
    # 5e proficiency progression
    if level <= 4: return 2
    if level <= 8: return 3
    if level <= 12: return 4
    if level <= 16: return 5
    return 6

async def fetch_json(url: str):
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

def markdown_from_draft(d: CharacterDraft, bs: BackstoryResult | None = None) -> str:
    lines = []
    lines.append(f"# {d.race} {d.cls} — Level {d.level}")
    lines.append("")
    lines.append(f"- **Background:** {d.background}")
    lines.append(f"- **Proficiency Bonus:** +{d.proficiency_bonus}")
    lines.append(f"- **Hit Die:** d{d.hit_die}")
    lines.append(f"- **Speed:** {d.speed} ft")
    lines.append(f"- **AC (no armor):** {d.armor_class_basic}")
    a = d.abilities
    lines.append(
        f"- **Abilities:** STR {a.STR} ({a.STR_mod:+}), DEX {a.DEX} ({a.DEX_mod:+}), "
        f"CON {a.CON} ({a.CON_mod:+}), INT {a.INT} ({a.INT_mod:+}), "
        f"WIS {a.WIS} ({a.WIS_mod:+}), CHA {a.CHA} ({a.CHA_mod:+})"
    )
    if d.saving_throws:
        lines.append(f"- **Saving Throws:** {', '.join(d.saving_throws)}")
    if d.languages:
        lines.append(f"- **Languages:** {', '.join(d.languages)}")
    if d.proficiencies:
        lines.append(f"- **Proficiencies:** {', '.join(p.name for p in d.proficiencies)}")
    if d.equipment:
        lines.append(f"- **Equipment:** {', '.join(d.equipment)}")
    lines.append("")
    if bs:
        lines.append("## Backstory")
        lines.append("")
        lines.append(bs.prose_markdown.strip())
        lines.append("")
        lines.append("### Traits / Ideals / Bonds / Flaws")
        lines.append(f"- **Traits:** {', '.join(bs.traits) or '—'}")
        lines.append(f"- **Ideals:** {', '.join(bs.ideals) or '—'}")
        lines.append(f"- **Bonds:** {', '.join(bs.bonds) or '—'}")
        lines.append(f"- **Flaws:** {', '.join(bs.flaws) or '—'}")
        if bs.hooks:
            lines.append(f"- **Hooks:** {', '.join(bs.hooks)}")
    return "\n".join(lines)

def markdown_from_progression(plan: ProgressionPlan, draft: CharacterDraft | None = None) -> str:
    lines: list[str] = []
    title = plan.name or (draft.name if draft and draft.name else None) or "Progression Plan"
    lines.append(f"# {title}")
    cls_name = draft.cls if draft else plan.class_index.title()
    lines.append("")
    lines.append(f"- Class: {cls_name}")
    if draft:
        lines.append(f"- Ancestry/Background: {draft.race} · {draft.background}")
    lines.append(f"- Target Level: {plan.target_level}")
    lines.append("")
    lines.append("## Level-by-Level")
    for p in plan.picks:
        hdr = f"### Level {p.level}"
        if p.subclass:
            hdr += f" — Subclass: {p.subclass}"
        lines.append(hdr)
        feats = ", ".join(p.features) if p.features else "—"
        lines.append(f"- Features: {feats}")
        if p.asi:
            lines.append(f"- ASI/Feat: {p.asi}")
        if p.spells_known:
            lines.append(f"- Spells Known: {', '.join(p.spells_known)}")
        if p.prepared:
            lines.append(f"- Prepared: {', '.join(p.prepared)}")
        if p.hp_gain is not None:
            lines.append(f"- HP Gain: {p.hp_gain}")
        if p.notes:
            lines.append("")
            lines.append(p.notes)
        lines.append("")
    if plan.notes_markdown:
        lines.append("## Notes")
        lines.append(plan.notes_markdown)
    return "\n".join(lines)
