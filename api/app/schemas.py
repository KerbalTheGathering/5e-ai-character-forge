from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# ---------- Rolls ----------
class AbilityRoll(BaseModel):
    dice: List[int] = Field(..., description="four d6 results, ascending")
    dropped_index: int = Field(..., description="0-3 index of the dropped die")
    total: int = Field(..., description="sum of top 3")

class AbilitySet(BaseModel):
    method: str = "4d6-drop-lowest"
    seed: int | None = None
    rolls: List[AbilityRoll]
    scores: List[int]  # six totals, typically sorted desc

# ---------- Character ----------
Ability = Literal["STR", "DEX", "CON", "INT", "WIS", "CHA"]

class GenerateInput(BaseModel):
    class_index: str
    race_index: str
    background_index: str
    level: int = 1
    scores: List[int]           # six numbers
    assignment: List[Ability]   # mapping for scores -> abilities

class AbilityBlock(BaseModel):
    STR: int; DEX: int; CON: int; INT: int; WIS: int; CHA: int
    STR_mod: int; DEX_mod: int; CON_mod: int; INT_mod: int; WIS_mod: int; CHA_mod: int

class Proficiency(BaseModel):
    type: str
    name: str
    source: Optional[str] = None

class CharacterDraft(BaseModel):
    name: Optional[str] = None
    level: int
    cls: str
    race: str
    background: str
    hit_die: int
    proficiency_bonus: int
    abilities: AbilityBlock
    speed: int
    saving_throws: List[str]
    languages: List[str]
    proficiencies: List[Proficiency] = []
    equipment: List[str] = []
    armor_class_basic: int
    features: List[str] = []
    spell_slots: Optional[dict[str, int]] = None  # e.g., {"1": 2, "2": 0, ...}

# ---------- Backstory ----------
class BackstoryInput(BaseModel):
    name: Optional[str] = None
    tone: Literal["heroic","grimdark","whimsical","noir","epic","custom"] = "custom"
    length: Literal["short","standard","long"] = "standard"
    include_hooks: bool = True
    custom_inspiration: Optional[str] = None
    draft: CharacterDraft

class BackstoryResult(BaseModel):
    summary: str
    traits: List[str]
    ideals: List[str]
    bonds: List[str]
    flaws: List[str]
    hooks: List[str]
    prose_markdown: str

# ---------- Export ----------
class ExportInput(BaseModel):
    draft: CharacterDraft
    backstory: Optional[BackstoryResult] = None
    # Optional progression plan to augment exports (MD/JSON)
    progression: Optional["ProgressionPlan"] = None

# ---------- Portrait & PDF ----------
class SaveInput(ExportInput):
    portrait_base64: Optional[str] = None  # PNG base64 (no data URL prefix)
    # Attach an optional progression plan to the character
    progression: Optional["ProgressionPlan"] = None

class ExportPDFInput(ExportInput):
    portrait_base64: Optional[str] = None
    # Include optional progression plan in the PDF
    progression: Optional["ProgressionPlan"] = None

# ---------- Magic Items ----------
class MagicItemInput(BaseModel):
    name: Optional[str] = None
    item_type: Optional[str] = None
    rarity: Optional[str] = None
    requires_attunement: Optional[bool] = None
    prompt: Optional[str] = None

class MagicItem(BaseModel):
    name: str
    item_type: str
    rarity: str
    requires_attunement: bool = False
    description: str
    properties: list[str] = []
    charges: Optional[int] = None
    # Optional mechanical fields
    bonus: Optional[int] = None
    damage: Optional[str] = None

class MagicItemExport(BaseModel):
    item: MagicItem

# ---------- Spells ----------
class SpellInput(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None  # 0 for cantrip
    school: Optional[str] = None
    classes: Optional[list[str]] = None  # e.g., ["Wizard","Sorcerer"]
    target: Optional[str] = None  # one | multiple | self | area
    intent: Optional[str] = None  # damage | healing | utility | control
    prompt: Optional[str] = None

class Spell(BaseModel):
    name: str
    level: int  # 0-9
    school: str
    classes: list[str] = []
    casting_time: str
    range: str
    duration: str
    components: str
    concentration: bool = False
    ritual: bool = False
    description: str
    damage: Optional[str] = None  # e.g., 3d10 lightning (half on save)
    save: Optional[str] = None  # e.g., DEX save half

class SpellExport(BaseModel):
    spell: Spell

# ---------- Progression Planner ----------
class LevelPick(BaseModel):
    level: int
    hp_gain: int | None = None
    features: list[str] = []
    subclass: str | None = None
    asi: str | None = None  # e.g., "+2 STR" or feat name
    spells_known: list[str] = []
    prepared: list[str] = []
    notes: str | None = None

class ProgressionInput(BaseModel):
    # Class index is needed to query SRD levels (e.g., "wizard")
    class_index: str
    target_level: int = 1
    allow_feats: bool = False
    style: Literal["martial","caster","face","balanced"] = "balanced"
    draft: CharacterDraft

class ProgressionPlan(BaseModel):
    name: str | None = None
    class_index: str
    target_level: int
    picks: list[LevelPick]
    notes_markdown: str = ""

class ProgressionExport(BaseModel):
    plan: ProgressionPlan

# ---------- Creatures ----------
class CreatureInput(BaseModel):
    name: Optional[str] = None
    size: Optional[str] = None  # Tiny, Small, Medium, Large, Huge, Gargantuan
    creature_type: Optional[str] = None  # Humanoid, Beast, Undead, etc.
    challenge_rating: Optional[str] = None  # e.g., "1/4", "1", "5"
    base_stat_block: Optional[str] = None  # Optional reference to base stat block
    prompt: Optional[str] = None

class Creature(BaseModel):
    name: str
    size: str
    creature_type: str
    challenge_rating: str
    armor_class: int
    hit_points: int
    hit_dice: str  # e.g., "5d8 + 10"
    speed: str  # e.g., "30 ft., climb 30 ft."
    ability_scores: AbilityBlock
    saving_throws: list[str] = []
    skills: list[str] = []
    damage_resistances: list[str] = []
    damage_immunities: list[str] = []
    condition_immunities: list[str] = []
    senses: str  # e.g., "darkvision 60 ft., passive Perception 12"
    languages: list[str] = []
    traits: list[str] = []  # Special traits from the provided list
    actions: list[str] = []  # Attack descriptions
    spells: list[str] = []  # Spell names if creature can cast spells
    description: str  # Flavor text description

class CreatureExport(BaseModel):
    creature: Creature
    prompt: Optional[str] = None
    portrait_base64: Optional[str] = None  # PNG base64 (no data URL prefix)
