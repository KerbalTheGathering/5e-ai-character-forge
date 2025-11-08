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
export type Tone = "heroic" | "grimdark" | "whimsical" | "noir" | "epic";
export type LengthOpt = "short" | "standard" | "long";
export interface BackstoryInput {
  name?: string | null;
  tone: Tone;
  length: LengthOpt;
  include_hooks: boolean;
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

export async function generateBackstory(body: BackstoryInput): Promise<BackstoryResult> {
  const res = await fetch(`${API}/api/backstory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`backstory failed: ${res.status}`);
  return res.json() as Promise<BackstoryResult>;
}

export async function downloadJSON(draft: CharacterDraft, backstory?: BackstoryResult | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/export/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null }),
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

export async function downloadMarkdown(draft: CharacterDraft, backstory?: BackstoryResult | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/export/md`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null }),
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

export async function saveToLibrary(draft: CharacterDraft, backstory?: BackstoryResult | null, portrait_base64?: string | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/library/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null, portrait_base64: portrait_base64 ?? null }),
  });
  if (!res.ok) throw new Error(`save failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string }>;
}

export async function listLibrary(limit = 10, page = 1, search: string = "", sort: string = "created_desc") {
  const q = new URLSearchParams({ limit: String(limit), page: String(page), sort });
  if (search) q.set('search', search);
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/library/list?${q.toString()}`);
  if (!res.ok) throw new Error(`list failed: ${res.status}`);
  return res.json() as Promise<{ items: {id:number; name:string; created_at:string}[]; total:number }>;
}

export async function getLibraryItem(id: number) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/library/get/${id}`);
  if (!res.ok) throw new Error(`get failed: ${res.status}`);
  return res.json() as Promise<{ id:number; name:string; created_at:string; draft: CharacterDraft; backstory: BackstoryResult | null; portrait_base64?: string | null }>;
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
}): Promise<MagicItem> {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/items/generate`, {
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
  return res.json() as Promise<{ items: {id:number; name:string; created_at:string}[]; total:number }>;
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

export async function generatePortrait(draft: CharacterDraft, backstory?: BackstoryResult | null): Promise<Blob> {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/portrait`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null }),
  });
  if (!res.ok) throw new Error(`portrait failed: ${res.status}`);
  return res.blob();
}

export async function downloadPDF(draft: CharacterDraft, backstory?: BackstoryResult | null, portrait_base64?: string | null) {
  const res = await fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/api/export/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, backstory: backstory ?? null, portrait_base64: portrait_base64 ?? null }),
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
