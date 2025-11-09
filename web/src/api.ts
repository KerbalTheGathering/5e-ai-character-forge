import type { APIList, APIRef } from "./types";

const API = `http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}`;

export type AbilityRoll = { dice: number[]; dropped_index: number; total: number };
export type AbilitySet = { method: string; seed?: number; rolls: AbilityRoll[]; scores: number[] };

export async function fetchRules<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API}/api/rules/${path}`);
  if (!res.ok) throw new Error(`rules fetch failed: ${res.status}`);
  return res.json() as Promise<T>;
}

// Convenience functions with concrete types
export async function listClasses(): Promise<APIRef[]> {
  const data = await fetchRules<APIList>("api/classes");
  return data.results;
}
export async function listRaces(): Promise<APIRef[]> {
  const data = await fetchRules<APIList>("api/races");
  return data.results;
}

export async function rollAbilities(seed?: number): Promise<AbilitySet> {
  const url = new URL(`${API}/api/roll/abilities`);
  if (seed !== undefined) url.searchParams.set("seed", String(seed));
  const res = await fetch(url);
  if (!res.ok) throw new Error(`roll failed: ${res.status}`);
  return res.json() as Promise<AbilitySet>;
}

export type Ability = "STR" | "DEX" | "CON" | "INT" | "WIS" | "CHA";

export interface AbilityBlock {
  STR: number; DEX: number; CON: number; INT: number; WIS: number; CHA: number;
  STR_mod: number; DEX_mod: number; CON_mod: number; INT_mod: number; WIS_mod: number; CHA_mod: number;
}
export interface CharacterDraft {
  name?: string | null;
  level: number;
  cls: string;
  race: string;
  background: string;           // <-- added
  hit_die: number;
  proficiency_bonus: number;
  abilities: AbilityBlock;
  speed: number;
  saving_throws: string[];
  languages: string[];
  proficiencies: { type: string; name: string; source?: string | null }[];
  equipment: string[];          // <-- added
  armor_class_basic: number;
  features: string[];           // <-- new
  spell_slots?: Record<string, number>; 
}

export async function generateDraft(params: {
  class_index: string;
  race_index: string;
  background_index: string;
  level: number;
  scores: number[];
  assignment: Ability[];
}): Promise<CharacterDraft> {
  const res = await fetch(`${API}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`generate failed: ${res.status}`);
  return res.json() as Promise<CharacterDraft>;
}

export async function listBackgrounds(): Promise<APIRef[]> {
  const data = await fetchRules<APIList>("api/backgrounds");
  return data.results;
}

// Backstory
export type Tone = "heroic" | "grimdark" | "whimsical" | "noir" | "epic" | "custom";
export type LengthOpt = "short" | "standard" | "long";
export interface BackstoryInput {
  name?: string | null;
  tone: Tone;
  length: LengthOpt;
  include_hooks: boolean;
  custom_inspiration?: string | null;
  draft: CharacterDraft;
}
export interface BackstoryResult {
  summary: string;
  traits: string[];
  ideals: string[];
  bonds: string[];
  flaws: string[];
  hooks: string[];
  prose_markdown: string;
}

export async function generateBackstory(body: BackstoryInput, engine: 'google'|'local' = 'google'): Promise<BackstoryResult> {
  const res = await fetch(`${API}/api/backstory?engine=${engine}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`backstory failed: ${res.status}`);
  return res.json() as Promise<BackstoryResult>;
}

export async function downloadJSON(draft: CharacterDraft, backstory?: BackstoryResult | null, progression?: ProgressionPlan | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/export/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null, progression: progression ?? null }),
  });
  if (!res.ok) throw new Error(`export json failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  // try to honor filename from header
  const cd = res.headers.get("Content-Disposition");
  a.download = cd?.match(/filename="(.+?)"/)?.[1] ?? "character.json";
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export async function downloadMarkdown(draft: CharacterDraft, backstory?: BackstoryResult | null, progression?: ProgressionPlan | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/export/md`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null, progression: progression ?? null }),
  });
  if (!res.ok) throw new Error(`export md failed: ${res.status}`);
  const text = await res.text();
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const cd = res.headers.get("Content-Disposition");
  a.download = cd?.match(/filename="(.+?)"/)?.[1] ?? "character.md";
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export async function saveToLibrary(draft: CharacterDraft, backstory?: BackstoryResult | null, portrait_base64?: string | null, progression?: ProgressionPlan | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/library/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null, portrait_base64: portrait_base64 ?? null, progression: progression ?? null }),
  });
  if (!res.ok) throw new Error(`save failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string }>;
}

export async function listLibrary(limit = 10, page = 1, search: string = "", sort: string = "created_desc") {
  const q = new URLSearchParams({ limit: String(limit), page: String(page), sort });
  if (search) q.set('search', search);
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/library/list?${q.toString()}`);
  if (!res.ok) throw new Error(`list failed: ${res.status}`);
  return res.json() as Promise<{ items: {id:number; name:string; created_at:string; cls?:string; race?:string}[]; total:number }>;
}

export async function getLibraryItem(id: number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/library/get/${id}`);
  if (!res.ok) throw new Error(`get failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string; draft: CharacterDraft; backstory: BackstoryResult | null; progression?: ProgressionPlan | null; portrait_base64?: string | null }>;
}

export async function deleteLibraryItem(id: number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/library/delete/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete failed: ${res.status}`);
  return res.json() as Promise<{ ok: true }>;
}

// ----- Magic Items -----
export interface MagicItem {
  name: string;
  item_type: string;
  rarity: string;
  requires_attunement?: boolean;
  description: string;
  properties: string[];
  charges?: number | null;
  bonus?: number | null;
  damage?: string | null;
}

export async function generateMagicItem(input: {
  name?: string | null;
  item_type?: string | null;
  rarity?: string | null;
  requires_attunement?: boolean | null;
  prompt?: string | null;
}, engine: 'google'|'local' = 'google'): Promise<MagicItem> {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/items/generate?engine=${engine}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`item generate failed: ${res.status}`);
  return res.json() as Promise<MagicItem>;
}

export async function saveMagicItem(item: MagicItem) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/items/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item }),
  });
  if (!res.ok) throw new Error(`item save failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string }>;
}

export async function listMagicItems(limit = 10, page = 1, search: string = "", sort: string = "created_desc") {
  const q = new URLSearchParams({ limit: String(limit), page: String(page), sort });
  if (search) q.set('search', search);
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/items/list?${q.toString()}`);
  if (!res.ok) throw new Error(`item list failed: ${res.status}`);
  return res.json() as Promise<{ items: {id:number; name:string; created_at:string; item_type?:string; rarity?:string}[]; total:number }>;
}

export async function getMagicItem(id: number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/items/get/${id}`);
  if (!res.ok) throw new Error(`item get failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string; item: MagicItem }>;
}

export async function deleteMagicItem(id: number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/items/delete/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`item delete failed: ${res.status}`);
  return res.json() as Promise<{ ok: true }>;
}

export function downloadItemJSON(item: MagicItem) {
  const blob = new Blob([JSON.stringify(item, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = `${item.name.replace(/\s+/g,'_')}_item.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export function downloadItemMarkdown(item: MagicItem) {
  const md = `# ${item.name}\n\n- Type: ${item.item_type}\n- Rarity: ${item.rarity}\n- Attunement: ${item.requires_attunement ? 'Yes' : 'No'}\n\n## Description\n${item.description}\n\n${item.properties?.length ? '## Properties\n- ' + item.properties.join('\n- ') + '\n' : ''}`;
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = `${item.name.replace(/\s+/g,'_')}.md`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export async function downloadItemPDF(item: MagicItem) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/items/export/pdf`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item }),
  });
  if (!res.ok) throw new Error(`item pdf failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url;
  const cd = res.headers.get('Content-Disposition');
  a.download = cd?.match(/filename="(.+?)"/)?.[1] ?? `${item.name.replace(/\s+/g,'_')}.pdf`;
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

// ----- Spells -----
export interface Spell {
  name: string;
  level: number;
  school: string;
  classes: string[];
  casting_time: string;
  range: string;
  duration: string;
  components: string;
  concentration?: boolean;
  ritual?: boolean;
  description: string;
  damage?: string | null;
  save?: string | null;
}

export async function generateSpell(input: {
  name?: string | null;
  level?: number | null;
  school?: string | null;
  classes?: string[] | null;
  target?: string | null;
  intent?: string | null;
  prompt?: string | null;
}, engine: 'google'|'local' = 'google'): Promise<Spell> {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/spells/generate?engine=${engine}`, {
    method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(input)
  });
  if (!res.ok) throw new Error(`spell generate failed: ${res.status}`);
  return res.json() as Promise<Spell>;
}

export async function saveSpell(spell: Spell) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/spells/save`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ spell })
  });
  if (!res.ok) throw new Error(`spell save failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string }>;
}

export async function listSpells(limit=10, page=1, search='', sort='created_desc') {
  const q = new URLSearchParams({ limit:String(limit), page:String(page), sort}); if (search) q.set('search', search);
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/spells/list?${q.toString()}`);
  if (!res.ok) throw new Error(`spells list failed: ${res.status}`);
  return res.json() as Promise<{ items:{id:number; name:string; created_at:string; level?:number; school?:string}[], total:number }>;
}

export async function getSpell(id:number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/spells/get/${id}`);
  if (!res.ok) throw new Error(`spell get failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string; spell: Spell }>;
}

export async function deleteSpell(id:number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/spells/delete/${id}`, { method:'DELETE' });
  if (!res.ok) throw new Error(`spell delete failed: ${res.status}`);
  return res.json() as Promise<{ ok:true }>;
}

export function downloadSpellJSON(spell: Spell) {
  const blob = new Blob([JSON.stringify(spell, null, 2)], { type:'application/json' });
  const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${spell.name.replace(/\s+/g,'_')}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export function downloadSpellMarkdown(spell: Spell) {
  const md = `# ${spell.name} (Level ${spell.level} ${spell.school})\n\n`+
    `- Classes: ${spell.classes.join(', ')}\n`+
    `- Casting Time: ${spell.casting_time}\n- Range: ${spell.range}\n- Duration: ${spell.duration}\n- Components: ${spell.components}\n- Concentration: ${spell.concentration? 'Yes':'No'}\n- Ritual: ${spell.ritual? 'Yes':'No'}\n\n`+
    `${spell.description}\n\n${spell.damage? `Damage: ${spell.damage}\n`:''}${spell.save? `Save: ${spell.save}\n`:''}`;
  const blob = new Blob([md], { type:'text/markdown' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${spell.name.replace(/\s+/g,'_')}.md`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export async function generatePortrait(draft: CharacterDraft, backstory?: BackstoryResult | null, engine: 'google'|'local' = 'google'): Promise<Blob> {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/portrait?engine=${engine}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null }),
  });
  if (!res.ok) throw new Error(`portrait failed: ${res.status}`);
  return res.blob();
}

export async function downloadPDF(draft: CharacterDraft, backstory?: BackstoryResult | null, portrait_base64?: string | null, progression?: ProgressionPlan | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/export/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null, portrait_base64: portrait_base64 ?? null, progression: progression ?? null }),
  });
  if (!res.ok) throw new Error(`export pdf failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const cd = res.headers.get("Content-Disposition");
  a.download = cd?.match(/filename="(.+?)"/)?.[1] ?? "character.pdf";
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

// --- Progression Planner ---

export interface LevelPick {
  level: number;
  hp_gain?: number | null;
  features: string[];
  subclass?: string | null;
  asi?: string | null;
  spells_known: string[];
  prepared: string[];
  notes?: string | null;
}

export interface ProgressionPlan {
  name?: string | null;
  class_index: string;
  target_level: number;
  picks: LevelPick[];
  notes_markdown: string;
}

export interface ProgressionInput {
  class_index: string;
  target_level: number;
  allow_feats?: boolean;
  style?: 'martial'|'caster'|'face'|'balanced';
  draft: CharacterDraft;
}

export async function generateProgression(input: ProgressionInput): Promise<ProgressionPlan> {
  const res = await fetch(`${API}/api/progression/generate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input)
  });
  if (!res.ok) throw new Error(`progression generate failed: ${res.status}`);
  return res.json() as Promise<ProgressionPlan>;
}

export async function downloadProgressionMarkdown(plan: ProgressionPlan) {
  const res = await fetch(`${API}/api/progression/export/md`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ plan })
  });
  if (!res.ok) throw new Error(`progression export md failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = (res.headers.get('Content-Disposition')?.match(/filename="(.+?)"/)?.[1] ?? 'progression.md');
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export async function saveProgression(plan: ProgressionPlan) {
  const res = await fetch(`${API}/api/progression/save`, { method:'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ plan }) });
  if (!res.ok) throw new Error(`progression save failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string }>;
}

export async function listProgressions(limit=10, page=1, search='', sort='created_desc') {
  const q = new URLSearchParams({ limit:String(limit), page:String(page), sort }); if (search) q.set('search', search);
  const res = await fetch(`${API}/api/progression/list?${q.toString()}`);
  if (!res.ok) throw new Error(`progression list failed: ${res.status}`);
  return res.json() as Promise<{ items:{id:number; name:string; created_at:string}[], total:number }>;
}

export async function getProgression(id:number) {
  const res = await fetch(`${API}/api/progression/get/${id}`);
  if (!res.ok) throw new Error(`progression get failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string; plan: ProgressionPlan }>;
}

export async function deleteProgression(id:number) {
  const res = await fetch(`${API}/api/progression/delete/${id}`, { method:'DELETE' });
  if (!res.ok) throw new Error(`progression delete failed: ${res.status}`);
  return res.json() as Promise<{ ok:true }>;
}

export async function downloadProgressionPDF(plan: ProgressionPlan) {
  const res = await fetch(`${API}/api/progression/export/pdf`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ plan })
  });
  if (!res.ok) throw new Error(`progression export pdf failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = (res.headers.get('Content-Disposition')?.match(/filename="(.+?)"/)?.[1] ?? 'progression.pdf');
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

// ----- Creatures -----
export interface Creature {
  name: string;
  size: string;
  creature_type: string;
  challenge_rating: string;
  armor_class: number;
  hit_points: number;
  hit_dice: string;
  speed: string;
  ability_scores: AbilityBlock;
  saving_throws: string[];
  skills: string[];
  damage_resistances: string[];
  damage_immunities: string[];
  condition_immunities: string[];
  senses: string;
  languages: string[];
  traits: string[];
  actions: string[];
  spells: string[];
  description: string;
}

export async function generateCreature(input: {
  name?: string | null;
  size?: string | null;
  creature_type?: string | null;
  challenge_rating?: string | null;
  base_stat_block?: string | null;
  prompt?: string | null;
}, engine: 'google'|'local' = 'google'): Promise<Creature> {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/creatures/generate?engine=${engine}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input)
  });
  if (!res.ok) throw new Error(`creature generate failed: ${res.status}`);
  return res.json() as Promise<Creature>;
}

export async function saveCreature(creature: Creature, portrait_base64?: string | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/creatures/save`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ creature, portrait_base64: portrait_base64 ?? null })
  });
  if (!res.ok) throw new Error(`creature save failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string }>;
}

export async function listCreatures(limit=10, page=1, search='', sort='created_desc') {
  const q = new URLSearchParams({ limit:String(limit), page:String(page), sort }); if (search) q.set('search', search);
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/creatures/list?${q.toString()}`);
  if (!res.ok) throw new Error(`creatures list failed: ${res.status}`);
  return res.json() as Promise<{ items:{id:number; name:string; created_at:string; size?:string; creature_type?:string; challenge_rating?:string}[], total:number }>;
}

export async function getCreature(id:number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/creatures/get/${id}`);
  if (!res.ok) throw new Error(`creature get failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string; creature: Creature; portrait_base64?: string | null }>;
}

export async function deleteCreature(id:number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/creatures/delete/${id}`, { method:'DELETE' });
  if (!res.ok) throw new Error(`creature delete failed: ${res.status}`);
  return res.json() as Promise<{ ok:true }>;
}

export function downloadCreatureJSON(creature: Creature) {
  const blob = new Blob([JSON.stringify(creature, null, 2)], { type:'application/json' });
  const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${creature.name.replace(/\s+/g,'_')}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export function downloadCreatureMarkdown(creature: Creature) {
  const md = `# ${creature.name}\n\n`+
    `- Size: ${creature.size}\n- Type: ${creature.creature_type}\n- Challenge Rating: ${creature.challenge_rating}\n`+
    `- Armor Class: ${creature.armor_class}\n- Hit Points: ${creature.hit_points} (${creature.hit_dice})\n- Speed: ${creature.speed}\n\n`+
    `## Ability Scores\n`+
    `- STR: ${creature.ability_scores.STR} (${creature.ability_scores.STR_mod >= 0 ? '+' : ''}${creature.ability_scores.STR_mod})\n`+
    `- DEX: ${creature.ability_scores.DEX} (${creature.ability_scores.DEX_mod >= 0 ? '+' : ''}${creature.ability_scores.DEX_mod})\n`+
    `- CON: ${creature.ability_scores.CON} (${creature.ability_scores.CON_mod >= 0 ? '+' : ''}${creature.ability_scores.CON_mod})\n`+
    `- INT: ${creature.ability_scores.INT} (${creature.ability_scores.INT_mod >= 0 ? '+' : ''}${creature.ability_scores.INT_mod})\n`+
    `- WIS: ${creature.ability_scores.WIS} (${creature.ability_scores.WIS_mod >= 0 ? '+' : ''}${creature.ability_scores.WIS_mod})\n`+
    `- CHA: ${creature.ability_scores.CHA} (${creature.ability_scores.CHA_mod >= 0 ? '+' : ''}${creature.ability_scores.CHA_mod})\n\n`+
    `${creature.saving_throws?.length ? `## Saving Throws\n- ${creature.saving_throws.join('\n- ')}\n\n` : ''}`+
    `${creature.skills?.length ? `## Skills\n- ${creature.skills.join('\n- ')}\n\n` : ''}`+
    `${creature.damage_resistances?.length ? `## Damage Resistances\n- ${creature.damage_resistances.join(', ')}\n\n` : ''}`+
    `${creature.damage_immunities?.length ? `## Damage Immunities\n- ${creature.damage_immunities.join(', ')}\n\n` : ''}`+
    `${creature.condition_immunities?.length ? `## Condition Immunities\n- ${creature.condition_immunities.join(', ')}\n\n` : ''}`+
    `## Senses\n${creature.senses}\n\n`+
    `${creature.languages?.length ? `## Languages\n- ${creature.languages.join(', ')}\n\n` : ''}`+
    `${creature.traits?.length ? `## Traits\n- ${creature.traits.join('\n- ')}\n\n` : ''}`+
    `${creature.actions?.length ? `## Actions\n- ${creature.actions.join('\n- ')}\n\n` : ''}`+
    `${creature.spells?.length ? `## Spells\n- ${creature.spells.join(', ')}\n\n` : ''}`+
    `## Description\n${creature.description}\n`;
  const blob = new Blob([md], { type:'text/markdown' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `${creature.name.replace(/\s+/g,'_')}.md`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

export async function generateCreaturePortrait(creature: Creature, engine: 'google'|'local' = 'google'): Promise<Blob> {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/creatures/portrait?engine=${engine}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ creature }),
  });
  if (!res.ok) throw new Error(`creature portrait failed: ${res.status}`);
  return res.blob();
}
