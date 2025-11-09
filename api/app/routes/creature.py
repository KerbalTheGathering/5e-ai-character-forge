from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from ..schemas import CreatureInput, Creature, CreatureExport, AbilityBlock
from ..ai_inference import use_local_inference, local_text_generate, google_text_generate, local_image_generate, google_image_generate
from ..database import create_item, get_item, list_items, delete_item, get_db_connection
from ..config import logger
import json
import base64

router = APIRouter()

CREATURE_GUIDE = (
    "You are a D&D 5e SRD-friendly designer. Create balanced, flavorful creatures. "
    "Follow Monster Manual-style format. Use the provided guidelines for creating creatures: "
    "You can alter size, creature type, ability scores (especially INT/WIS/CHA), languages, "
    "proficiencies, senses, spells, attacks (name/flavor/damage type), resistances/immunities, "
    "and traits. Avoid copyrighted setting names."
)

@router.post("/api/creatures/generate", response_model=Creature)
async def creatures_generate(payload: CreatureInput, engine: str | None = Query(default=None)):
    logger.debug("creatures: generate request name=%s size=%s type=%s cr=%s", 
                 payload.name, payload.size, payload.creature_type, payload.challenge_rating)
    
    name = payload.name or "Unnamed Creature"
    size = payload.size or "Medium"
    creature_type = payload.creature_type or "Humanoid"
    cr = payload.challenge_rating or "1"
    base_stat = payload.base_stat_block or ""
    
    long_prompt = (
        "Using the following inputs, design a single D&D 5e creature stat block and return JSON ONLY with keys: "
        "name, size, creature_type, challenge_rating, armor_class, hit_points, hit_dice, speed, "
        "ability_scores (object with STR, DEX, CON, INT, WIS, CHA and corresponding _mod fields), "
        "saving_throws (array of strings), skills (array of strings), "
        "damage_resistances (array of strings), damage_immunities (array of strings), "
        "condition_immunities (array of strings), senses (string), languages (array of strings), "
        "traits (array of strings from: Aversion to Fire, Battle Ready, Beast Whisperer, Death Jinx, "
        "Dimensional Disruption, Disciple of the Nine Hells, Disintegration, Emissary of Juiblex, "
        "Fey Ancestry, Forbiddance, Gloom Shroud, Light, Mimicry, Poison Tolerant, Resonant Connection, "
        "Siege Monster, Slaad Host, Steadfast, Telepathic Bond, Telepathic Shroud, Ventriloquism, "
        "Warrior's Wrath, Wild Talent), "
        "actions (array of strings describing attacks), spells (array of spell names if applicable), "
        "description (flavor text).\n"
        f"Inputs: name={name}; size={size}; creature_type={creature_type}; challenge_rating={cr}.\n"
        + (f"Base stat block reference: {base_stat}.\n" if base_stat else "")
        + "Guidelines: Balance the creature for its CR. Use standard ability score modifiers. "
        "Include appropriate senses (darkvision, blindsight, etc.). Add interesting traits and actions. "
        + (payload.prompt or "")
    )
    
    try:
        if use_local_inference(engine):
            text = await local_text_generate(long_prompt)
        else:
            text = await google_text_generate(long_prompt, CREATURE_GUIDE)
        
        if text.startswith("```"):
            text = text.strip("`").replace("json\n", "").replace("\njson", "")
        
        data = json.loads(text)
        
        # Normalize ability scores
        ab_data = data.get("ability_scores", {})
        if not isinstance(ab_data, dict):
            ab_data = {}
        # Ensure all abilities are present
        for ab in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            if ab not in ab_data:
                ab_data[ab] = 10
            # Calculate modifiers if not present
            mod_key = f"{ab}_mod"
            if mod_key not in ab_data:
                ab_data[mod_key] = (ab_data[ab] - 10) // 2
        
        ab_scores = AbilityBlock(
            STR=ab_data.get("STR", 10), DEX=ab_data.get("DEX", 10), CON=ab_data.get("CON", 10),
            INT=ab_data.get("INT", 10), WIS=ab_data.get("WIS", 10), CHA=ab_data.get("CHA", 10),
            STR_mod=ab_data.get("STR_mod", 0), DEX_mod=ab_data.get("DEX_mod", 0), CON_mod=ab_data.get("CON_mod", 0),
            INT_mod=ab_data.get("INT_mod", 0), WIS_mod=ab_data.get("WIS_mod", 0), CHA_mod=ab_data.get("CHA_mod", 0),
        )
        
        # Normalize lists
        def to_list(v):
            if isinstance(v, list):
                return [str(x) for x in v if x]
            if isinstance(v, str):
                return [x.strip() for x in v.split(",") if x.strip()]
            return []
        
        creature = Creature(
            name=str(data.get("name", name)),
            size=str(data.get("size", size)),
            creature_type=str(data.get("creature_type", creature_type)),
            challenge_rating=str(data.get("challenge_rating", cr)),
            armor_class=int(data.get("armor_class", 10)),
            hit_points=int(data.get("hit_points", 10)),
            hit_dice=str(data.get("hit_dice", "1d8")),
            speed=str(data.get("speed", "30 ft.")),
            ability_scores=ab_scores,
            saving_throws=to_list(data.get("saving_throws", [])),
            skills=to_list(data.get("skills", [])),
            damage_resistances=to_list(data.get("damage_resistances", [])),
            damage_immunities=to_list(data.get("damage_immunities", [])),
            condition_immunities=to_list(data.get("condition_immunities", [])),
            senses=str(data.get("senses", "passive Perception 10")),
            languages=to_list(data.get("languages", [])),
            traits=to_list(data.get("traits", [])),
            actions=to_list(data.get("actions", [])),
            spells=to_list(data.get("spells", [])),
            description=str(data.get("description", "")),
        )
        return creature
    except Exception as e:
        logger.exception("creatures: generation failed")
        raise HTTPException(502, f"creature generation failed: {e}")

@router.post("/api/creatures/portrait")
async def creatures_portrait(payload: CreatureExport, engine: str | None = Query(default=None)):
    logger.info("Generating creature portrait image...")
    try:
        logger.info("Constructing creature portrait prompt...")
        c = payload.creature
        name = c.name or "Unnamed Creature"
        abilities = c.ability_scores
        prompt = (
            f"Create a detailed fantasy portrait of a D&D 5e creature.\n"
            f"Name: {name}. Size: {c.size}. Type: {c.creature_type}. Challenge Rating: {c.challenge_rating}.\n"
            f"Key abilities: STR {abilities.STR}, DEX {abilities.DEX}, CON {abilities.CON}, INT {abilities.INT}, WIS {abilities.WIS}, CHA {abilities.CHA}.\n"
            f"Description: {c.description[:500] if c.description else ''}\n"
        )
        if c.traits:
            prompt += f"Special traits: {', '.join(c.traits[:5])}.\n"
    except Exception as e:
        raise HTTPException(400, f"creature portrait prompt construction failed: {e}")
    try:
        if use_local_inference(engine):
            logger.info("Using local image generation...")
            image_bytes = await local_image_generate(prompt)
        else:
            logger.info("Using Gemini image generation...")
            image_bytes = await google_image_generate(prompt)
    except Exception as e:
        logger.exception("Image generation failed")
        raise HTTPException(502, f"image generation failed: {e}")
    try:
        logger.info("creature portrait bytes: %d bytes%s", len(image_bytes),
                    " (png)" if image_bytes.startswith(b"\x89PNG\r\n\x1a\n") else "")
    except Exception:
        pass
    filename = f"{(name or c.creature_type).replace(' ','_')}_portrait.png"
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(image_bytes)),
            "Cache-Control": "no-store",
        },
    )

@router.post("/api/creatures/save")
async def creatures_save(payload: CreatureExport):
    logger.debug("creatures: save %s", payload.creature.name)
    portrait_blob = None
    if hasattr(payload, "portrait_base64") and payload.portrait_base64:
        try:
            portrait_blob = base64.b64decode(payload.portrait_base64)
        except Exception:
            portrait_blob = None
    creature_data = {
        "name": payload.creature.name,
        "creature_json": payload.creature.model_dump_json(),
        "prompt": payload.prompt if hasattr(payload, "prompt") else None,
        "portrait_png": portrait_blob
    }
    result = create_item("creature_library", creature_data)
    return result

@router.get("/api/creatures/list")
async def creatures_list(limit: int = 10, page: int = 1, search: str | None = None, sort: str = "created_desc"):
    logger.debug("creatures: list limit=%s page=%s search=%s sort=%s", limit, page, search, sort)
    result = list_items("creature_library", limit, page, search, sort)
    # Enrich items with size, type, and CR from creature_json
    con = get_db_connection()
    for item in result["items"]:
        row = con.execute("SELECT creature_json FROM creature_library WHERE id = ?", (item["id"],)).fetchone()
        if row:
            try:
                creature_data = json.loads(row["creature_json"])
                item["size"] = creature_data.get("size", "")
                item["creature_type"] = creature_data.get("creature_type", "")
                item["challenge_rating"] = creature_data.get("challenge_rating", "")
            except Exception:
                item["size"] = ""
                item["creature_type"] = ""
                item["challenge_rating"] = ""
    con.close()
    return result

@router.get("/api/creatures/get/{creature_id}")
async def creatures_get(creature_id: int):
    logger.debug("creatures: get id=%s", creature_id)
    row = get_item("creature_library", creature_id)
    if not row:
        raise HTTPException(404, "Not found")
    creature = json.loads(row["creature_json"])
    portrait_b64 = None
    if "portrait_png" in row.keys() and row["portrait_png"] is not None:
        try:
            portrait_b64 = base64.b64encode(row["portrait_png"]).decode("ascii")
        except Exception:
            portrait_b64 = None
    return {
        "id": row["id"],
        "name": row["name"],
        "created_at": row["created_at"],
        "creature": creature,
        "portrait_base64": portrait_b64
    }

@router.delete("/api/creatures/delete/{creature_id}")
async def creatures_delete(creature_id: int):
    logger.debug("creatures: delete id=%s", creature_id)
    ok = delete_item("creature_library", creature_id)
    if not ok:
        raise HTTPException(404, "Not found")
    return {"ok": True}

