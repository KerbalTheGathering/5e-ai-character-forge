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
    tone: Literal["heroic","grimdark","whimsical","noir","epic"] = "heroic"
    length: Literal["short","standard","long"] = "standard"
    include_hooks: bool = True
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

# ---------- Portrait & PDF ----------
class SaveInput(ExportInput):
    portrait_base64: Optional[str] = None  # PNG base64 (no data URL prefix)

class ExportPDFInput(ExportInput):
    portrait_base64: Optional[str] = None

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
