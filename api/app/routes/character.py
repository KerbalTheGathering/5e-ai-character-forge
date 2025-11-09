from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List
from ..schemas import AbilitySet, GenerateInput, CharacterDraft, AbilityBlock, Proficiency
from ..rollers import roll_ability_set
from ..helpers import fetch_json, pb
from ..config import RULES_BASE, RULES_API_PREFIX, logger

router = APIRouter()

@router.get("/api/roll/abilities", response_model=AbilitySet)
async def roll_abilities(seed: int | None = Query(default=None, description="optional seed for reproducibility")):
    logger.debug("roll_abilities: seed=%s", seed)
    return roll_ability_set(seed)

@router.post("/api/generate", response_model=CharacterDraft)
async def generate_character(payload: GenerateInput):
    logger.debug("generate_character: class=%s race=%s background=%s level=%s", payload.class_index, payload.race_index, payload.background_index, payload.level)
    # fetch class / race / background
    cls = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{payload.class_index}")
    race = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/races/{payload.race_index}")
    bg   = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/backgrounds/{payload.background_index}")

    # scores -> abilities
    if len(payload.scores) != 6 or len(payload.assignment) != 6:
        raise HTTPException(400, "scores and assignment must each have length 6")
    ability_map: Dict[str,int] = {}
    for score, abil in zip(payload.scores, payload.assignment):
        ability_map[abil] = score
    for k in ["STR","DEX","CON","INT","WIS","CHA"]:
        if k not in ability_map: raise HTTPException(400, f"missing ability in assignment: {k}")

    ab = AbilityBlock(
        STR=ability_map["STR"], DEX=ability_map["DEX"], CON=ability_map["CON"],
        INT=ability_map["INT"], WIS=ability_map["WIS"], CHA=ability_map["CHA"],
        STR_mod=(ability_map["STR"]-10)//2, DEX_mod=(ability_map["DEX"]-10)//2, CON_mod=(ability_map["CON"]-10)//2,
        INT_mod=(ability_map["INT"]-10)//2, WIS_mod=(ability_map["WIS"]-10)//2, CHA_mod=(ability_map["CHA"]-10)//2,
    )
    level = max(1, min(payload.level, 20))
    hit_die = int(cls.get("hit_die", 8))
    saves = [st["name"] for st in cls.get("saving_throws", [])]

    # languages from race + background (options not chosen yet)
    langs = [l["name"] for l in race.get("languages", [])]
    langs += [l["name"] for l in bg.get("languages", [])] if bg.get("languages") else []

    # proficiencies
    profs: List[Proficiency] = []
    for p in cls.get("proficiencies", []):
        profs.append(Proficiency(type="proficiency", name=p["name"], source="class"))
    for p in race.get("starting_proficiencies", []):
        profs.append(Proficiency(type="proficiency", name=p["name"], source="race"))
    for p in bg.get("starting_proficiencies", []):
        profs.append(Proficiency(type="proficiency", name=p["name"], source="background"))

    # equipment: class starting_equipment + background starting_equipment
    equip: List[str] = []
    try:
        cls_eq = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/starting-equipment/{payload.class_index}")
        for item in cls_eq.get("starting_equipment", []):
            equip.append(f"{item.get('quantity','1')}x {item['equipment']['name']}")
    except Exception:
        pass
    for item in bg.get("starting_equipment", []) or []:
        equip.append(f"{item.get('quantity','1')}x {item['equipment']['name']}")

    # NEW: class features & spell slots at this level (compute BEFORE constructing draft)
    lvl_data = await fetch_json(f"{RULES_BASE}/{RULES_API_PREFIX}/classes/{payload.class_index}/levels/{level}")
    feat_names = [f["name"] for f in lvl_data.get("features", [])]

    slots: dict[str, int] | None = None
    sc = lvl_data.get("spellcasting")
    if sc:
        slots = {}
        for k, v in sc.items():
            if k.startswith("spell_slots_level_"):
                n = k.split("_")[-1]
                try:
                    slots[n] = int(v or 0)
                except Exception:
                    pass

    # construct draft (now include features & spell_slots)
    draft = CharacterDraft(
        level=level,
        cls=cls.get("name", payload.class_index),
        race=race.get("name", payload.race_index),
        background=bg.get("name", payload.background_index),
        hit_die=hit_die,
        proficiency_bonus=pb(level),
        abilities=ab,
        speed=int(race.get("speed", 30)),
        saving_throws=saves,
        languages=sorted(list(dict.fromkeys(langs))),
        proficiencies=profs,
        equipment=equip,
        armor_class_basic=10 + ab.DEX_mod,
        features=feat_names,
        spell_slots=slots,
    )
    return draft
