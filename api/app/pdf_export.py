import io
import base64
from io import BytesIO
from fastapi import HTTPException
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from textwrap import wrap
from .schemas import CharacterDraft, MagicItem, ProgressionPlan, BackstoryResult

# --- PDF Helpers ---

def _get_now_formatted() -> str:
    try:
        return __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')
    except Exception:
        return ''

def _wrap_text_reportlab(canvas_obj: canvas.Canvas, text: str, max_width: float, font: str = "Helvetica", size: int = 10) -> list[str]:
    canvas_obj.setFont(font, size)
    words = text.split()
    lines: list[str] = []
    line = ""
    for w in words:
        test = (line + (" " if line else "") + w)
        if canvas_obj.stringWidth(test, font, size) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            if canvas_obj.stringWidth(w, font, size) > max_width:
                accum = ""
                for ch in w:
                    if canvas_obj.stringWidth(accum + ch, font, size) <= max_width:
                        accum += ch
                    else:
                        lines.append(accum)
                        accum = ch
                line = accum
            else:
                line = w
    if line:
        lines.append(line)
    return lines

def _draw_footer(canvas_obj: canvas.Canvas, width: float, margin: float):
    canvas_obj.setFont("Helvetica", 9)
    page_text = f"Page {canvas_obj.getPageNumber()}  •  Generated {_get_now_formatted()}"
    canvas_obj.drawRightString(width - margin, margin * 0.6, page_text)

def _draw_title(canvas_obj: canvas.Canvas, text: str, margin: float, height: float):
    canvas_obj.setFont("Helvetica-Bold", 18)
    canvas_obj.drawString(margin, height - margin + 0.1*inch, text)

def _draw_block(canvas_obj: canvas.Canvas, x: float, y_top: float, text_lines: list[str], width_avail: float, margin: float, height: float, title_text: str, leading: float = 14, font: str = "Helvetica", size: int = 10) -> float:
    canvas_obj.setFont(font, size)
    y = y_top
    for raw in text_lines:
        for ln in _wrap_text_reportlab(canvas_obj, raw, width_avail, font, size):
            if y <= margin:
                _draw_footer(canvas_obj, canvas_obj._pagesize[0], margin)
                canvas_obj.showPage()
                _draw_title(canvas_obj, title_text, margin, height)
                y = height - margin - 0.25*inch
                canvas_obj.setFont(font, size)
            canvas_obj.drawString(x, y, ln)
            y -= leading
    return y

def _draw_section(canvas_obj: canvas.Canvas, x: float, y_top: float, title_text: str, body_lines: list[str], width_avail: float, margin: float, height: float) -> float:
    canvas_obj.setFont("Helvetica-Bold", 12)
    y_local = y_top
    if y_local <= margin:
        _draw_footer(canvas_obj, canvas_obj._pagesize[0], margin)
        canvas_obj.showPage()
        _draw_title(canvas_obj, title_text, margin, height)
        y_local = height - margin - 0.25*inch
    canvas_obj.drawString(x, y_local, title_text)
    y_local -= 14
    return _draw_block(canvas_obj, x, y_local, body_lines, width_avail, margin, height, title_text, leading=13, font="Helvetica", size=10)

# --- Exporters ---

async def export_magic_item_pdf_content(item: MagicItem) -> BytesIO:
    try:
        # Ensure reportlab is installed
        pass
    except Exception as e:
        raise HTTPException(500, f"PDF generation libs missing: {e}")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 0.75*inch

    _draw_title(c, f"{item.name} — {item.item_type} · {item.rarity}", margin, height)
    y = height - 1.25*inch
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Attunement: {'Required' if item.requires_attunement else 'No'}")
    y -= 16

    for line in wrap(item.description or "", 98):
        c.drawString(margin, y, line); y -= 14
        if y < 1*inch: _draw_footer(c, width, margin); c.showPage(); y = height - 0.9*inch

    if item.properties:
        y -= 8
        c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Properties"); y -= 16; c.setFont("Helvetica", 11)
        for p in item.properties:
            for line in wrap(p, 95):
                c.drawString(margin + 0.15*inch, y, f"• {line}" if line == p else f"  {line}"); y -= 14
                if y < 1*inch: _draw_footer(c, width, margin); c.showPage(); y = height - 0.9*inch

    _draw_footer(c, width, margin); c.showPage(); c.save(); buffer.seek(0)
    return buffer

async def export_progression_pdf_content(plan: ProgressionPlan) -> BytesIO:
    try:
        # Ensure reportlab is installed
        pass
    except Exception as e:
        raise HTTPException(500, f"PDF generation libs missing: {e}")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    margin = 0.75*inch
    content_width = width - 2*margin

    title = (plan.name or "Progression Plan")
    _draw_title(c, title, margin, height)
    y = height - margin - 0.35*inch

    summary = [
        f"Class: {plan.class_index.title()}",
        f"Target Level: {plan.target_level}",
    ]
    y = _draw_block(c, margin, y, summary, content_width, margin, height, title, leading=13)

    for p in plan.picks:
        y -= 8
        c.setFont("Helvetica-Bold", 12)
        hdr = f"Level {p.level}"
        if p.subclass:
            hdr += f" — Subclass: {p.subclass}"
        if y <= margin:
            _draw_footer(c, width, margin); c.showPage(); _draw_title(c, title, margin, height); y = height - margin - 0.35*inch
        c.drawString(margin, y, hdr); y -= 14
        body: list[str] = []
        body.append(f"Features: {', '.join(p.features) if p.features else '—'}")
        if p.asi:
            body.append(f"ASI/Feat: {p.asi}")
        if p.spells_known:
            body.append(f"Spells Known: {', '.join(p.spells_known)}")
        if p.prepared:
            body.append(f"Prepared: {', '.join(p.prepared)}")
        if p.hp_gain is not None:
            body.append(f"HP Gain: {p.hp_gain}")
        if p.notes:
            body.append(p.notes)
        y = _draw_block(c, margin, y, body, content_width, margin, height, title, leading=13)

    if plan.notes_markdown:
        _draw_footer(c, width, margin); c.showPage(); _draw_title(c, title, margin, height)
        y = height - margin - 0.35*inch
        c.setFont("Helvetica-Bold", 12); c.drawString(margin, y, "Notes"); y -= 14
        y = _draw_block(c, margin, y, [plan.notes_markdown], content_width, margin, height, title, leading=13)

    _draw_footer(c, width, margin); c.showPage(); c.save(); buffer.seek(0)
    return buffer

async def export_character_pdf_content(draft: CharacterDraft, backstory: BackstoryResult | None, progression: ProgressionPlan | None, portrait_base64: str | None) -> BytesIO:
    try:
        # Ensure reportlab is installed
        pass
    except Exception as e:
        raise HTTPException(500, f"PDF generation libs missing: {e}")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    margin = 0.75*inch
    gutter = 0.4*inch
    content_width = width - 2*margin

    title = (draft.name or f"{draft.race} {draft.cls}") + f" — Level {draft.level}"
    _draw_title(c, title, margin, height)

    y = height - margin - 0.35*inch

    left_x = margin
    info_x = margin
    info_width = content_width
    img_h = 0
    if portrait_base64:
        try:
            img_bytes = base64.b64decode(portrait_base64)
            img = ImageReader(BytesIO(img_bytes))
            img_w = 2.3*inch
            img_h = 2.9*inch
            c.drawImage(img, left_x, y - img_h + 0.15*inch, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
            info_x = left_x + img_w + gutter
            info_width = content_width - (img_w + gutter)
        except Exception:
            pass

    d = draft
    a = d.abilities
    stats_lines = [
        f"Background: {d.background}",
        f"Proficiency Bonus: +{d.proficiency_bonus}",
        f"Hit Die: d{d.hit_die} · Speed: {d.speed} ft · AC (no armor): {d.armor_class_basic}",
        f"Abilities: STR {a.STR} ({a.STR_mod:+}), DEX {a.DEX} ({a.DEX_mod:+}), CON {a.CON} ({a.CON_mod:+}), INT {a.INT} ({a.INT_mod:+}), WIS {a.WIS} ({a.WIS_mod:+}), CHA {a.CHA} ({a.CHA_mod:+})",
    ]
    y_after = _draw_section(c, info_x, y - 0.1*inch, "Stats", stats_lines, info_width, margin, height)

    if d.saving_throws:
        y_after = _draw_section(c, info_x, y_after - 6, "Saving Throws", [", ".join(d.saving_throws)], info_width, margin, height)
    if d.languages:
        y_after = _draw_section(c, info_x, y_after - 6, "Languages", [", ".join(d.languages)], info_width, margin, height)
    if d.proficiencies:
        y_after = _draw_section(c, info_x, y_after - 6, "Proficiencies", [", ".join(p.name for p in d.proficiencies)], info_width, margin, height)
    if d.equipment:
        y_after = _draw_section(c, info_x, y_after - 6, "Equipment", [", ".join(d.equipment)], info_width, margin, height)
    if d.features:
        y_after = _draw_section(c, info_x, y_after - 6, f"Features @ Level {d.level}", [", ".join(d.features)], info_width, margin, height)

    y = min(y_after, y - img_h - 0.2*inch)

    if backstory:
        _draw_footer(c, width, margin); c.showPage()
        _draw_title(c, "Backstory", margin, height)
        c.setFont("Helvetica", 11)
        prose = backstory.prose_markdown
        y2 = height - margin - 0.35*inch
        para_leading = 15
        for paragraph in [p for p in prose.split("\n\n") if p.strip()]:
            for ln in _wrap_text_reportlab(c, paragraph, content_width, "Helvetica", 11):
                if y2 <= margin:
                    _draw_footer(c, width, margin); c.showPage(); _draw_title(c, "Backstory", margin, height); y2 = height - margin - 0.35*inch; c.setFont("Helvetica", 11)
                c.drawString(margin, y2, ln)
                y2 -= para_leading

    if progression:
        try:
            plan = progression
            _draw_footer(c, width, margin); c.showPage()
            _draw_title(c, "Progression Plan", margin, height)
            y3 = height - margin - 0.35*inch
            c.setFont("Helvetica-Bold", 11)
            cols = [
                ("Level", 0.9*inch),
                ("Features", 3.3*inch),
                ("Subclass", 1.4*inch),
                ("ASI/Feat", 1.2*inch),
                ("HP", 0.7*inch),
            ]
            x = margin
            for title_text, w in cols:
                c.drawString(x, y3, title_text)
                x += w
            y3 -= 14
            c.setFont("Helvetica", 10)
            for p in plan.picks:
                if y3 <= margin:
                    _draw_footer(c, width, margin); c.showPage(); _draw_title(c, "Progression Plan", margin, height); y3 = height - margin - 0.35*inch; c.setFont("Helvetica", 10)
                    x = margin
                    c.setFont("Helvetica-Bold", 11)
                    for title_text, w in cols:
                        c.drawString(x, y3, title_text); x += w
                    y3 -= 14; c.setFont("Helvetica", 10)
                x = margin
                col_vals = [
                    str(p.level),
                    ", ".join(p.features) if (p.features or []) else "—",
                    (p.subclass or "—"),
                    (p.asi or "—"),
                    (str(p.hp_gain) if (p.hp_gain is not None) else "—"),
                ]
                widths = [w for _, w in cols]
                lines_per_col: list[list[str]] = []
                for (val, w) in zip(col_vals, widths):
                    lines_per_col.append(_wrap_text_reportlab(c, val, w))
                row_height = max(len(col) for col in lines_per_col) * 13
                max_lines = max(len(col) for col in lines_per_col)
                for line_idx in range(max_lines):
                    x = margin
                    for col_idx, w in enumerate(widths):
                        text_line = lines_per_col[col_idx][line_idx] if line_idx < len(lines_per_col[col_idx]) else ""
                        c.drawString(x, y3, text_line)
                        x += w
                    y3 -= 13
            if getattr(plan, 'notes_markdown', None):
                y3 -= 10
                c.setFont("Helvetica-Bold", 11); c.drawString(margin, y3, "Notes"); y3 -= 14; c.setFont("Helvetica", 10)
                y3 = _draw_block(c, margin, y3, [plan.notes_markdown], content_width, margin, height, title)
        except Exception:
            pass

    _draw_footer(c, width, margin); c.showPage(); c.save()
    buffer.seek(0)
    return buffer
