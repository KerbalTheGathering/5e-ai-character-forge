import { useEffect, useMemo, useState } from "react";
import "./App.css";
import {
  rollAbilities, type AbilitySet,
  listClasses, listRaces, listBackgrounds,
  generateDraft, type CharacterDraft, type Ability,
  generateBackstory, type BackstoryResult,
  type Tone, type LengthOpt,
  downloadJSON, downloadMarkdown,
  saveToLibrary, listLibrary, getLibraryItem, deleteLibraryItem
} from "./api";
import type { APIRef } from "./types";
import GlassCard from "./components/GlassCard";
import { Tabs } from "./components/Tabs";
// tabs removed in favor of sidebar
import PickersPanel from "./components/PickersPanel";
import AbilitiesPanel from "./components/AbilitiesPanel";
import DraftPanel from "./components/DraftPanel";
import BackstoryPanel from "./components/BackstoryPanel";
// LibraryPanel no longer used; tables replace it
import MagicItemForm from "./components/MagicItemForm";
import MagicItemPreview from "./components/MagicItemPreview";
import SpellForm from "./components/SpellForm";
import SpellPreview from "./components/SpellPreview";
import CharLibraryTable from "./components/CharLibraryTable";
import ItemLibraryTable from "./components/ItemLibraryTable";
import SpellLibraryTable from "./components/SpellLibraryTable";
// Progression library is now integrated with character save
import { generatePortrait, downloadPDF, generateMagicItem, saveMagicItem, listMagicItems, getMagicItem, deleteMagicItem, type MagicItem, generateSpell, saveSpell, listSpells, getSpell, deleteSpell, type Spell } from "./api";
import Sidebar from "./components/Sidebar";
import ProgressionPanel from "./components/ProgressionPanel";
import LoadingButton from "./components/LoadingButton";

// Class ability priorities (indices from dnd5eapi)
const CLASS_PRIORITIES: Record<string, Ability[]> = {
  barbarian: ["STR","CON","DEX","WIS","CHA","INT"],
  bard:      ["CHA","DEX","CON","WIS","INT","STR"],
  cleric:    ["WIS","CON","STR","DEX","CHA","INT"],
  druid:     ["WIS","CON","DEX","INT","CHA","STR"],
  fighter:   ["STR","CON","DEX","WIS","INT","CHA"],
  monk:      ["DEX","WIS","CON","STR","INT","CHA"],
  paladin:   ["STR","CHA","CON","WIS","DEX","INT"],
  ranger:    ["DEX","WIS","CON","STR","INT","CHA"],
  rogue:     ["DEX","INT","CON","WIS","CHA","STR"],
  sorcerer:  ["CHA","CON","DEX","WIS","INT","STR"],
  warlock:   ["CHA","CON","DEX","WIS","INT","STR"],
  wizard:    ["INT","CON","DEX","WIS","CHA","STR"],
};

const GOOGLE_KEY_PRESENT = Boolean(import.meta.env.VITE_GOOGLE_API_KEY);

function autoAssignmentForClass(classIndex: string): Ability[] {
  const order = CLASS_PRIORITIES[classIndex] ?? ["STR","DEX","CON","INT","WIS","CHA"];
  // scores are already sorted desc; map highest→order[0], etc.
  // But our UI expects "assignment[i] is the ability for scores[i]"
  return order.slice(0, 6) as Ability[];
}

function randPick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

export default function App() {
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [classes, setClasses] = useState<APIRef[] | null>(null);
  const [races, setRaces] = useState<APIRef[] | null>(null);
  const [backgrounds, setBackgrounds] = useState<APIRef[] | null>(null);

  const [selectedClass, setSelectedClass] = useState<string>("");
  const [selectedRace, setSelectedRace] = useState<string>("");
  const [selectedBackground, setSelectedBackground] = useState<string>("");

  const [level, setLevel] = useState<number>(1);
  const [abilities, setAbilities] = useState<AbilitySet | null>(null);
  const [seed, setSeed] = useState<string>("");
  const [assignment, setAssignment] = useState<Ability[]>(["STR","DEX","CON","INT","WIS","CHA"]);
  const [draft, setDraft] = useState<CharacterDraft | null>(null);
  const [charName, setCharName] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [portraitBase64, setPortraitBase64] = useState<string | null>(null);
  const [portraitUrl, setPortraitUrl] = useState<string | null>(null);
  // Nav section (progression integrated into character flow)
  type Section = "home" | "char-new" | "char-lib" | "item-new" | "item-lib" | "spell-new" | "spell-lib";
  const [section, setSection] = useState<Section>("home");

  // backstory
  const [tone, setTone] = useState<Tone>("custom");
  const [lengthOpt, setLengthOpt] = useState<LengthOpt>("standard");
  const [includeHooks, setIncludeHooks] = useState(true);
  const [customInspiration, setCustomInspiration] = useState("");
  const [backstory, setBackstory] = useState<BackstoryResult | null>(null);
  const [busyBS, setBusyBS] = useState(false);
  const [lib, setLib] = useState<{id:number; name:string; created_at:string}[] | null>(null);
  const [busyLib, setBusyLib] = useState(false);  
  const [charPage, setCharPage] = useState(1);
  const charPageSize = 8;
  const [charTotal, setCharTotal] = useState(0);
  const [charSearch, setCharSearch] = useState("");
  const [charSort, setCharSort] = useState("created_desc");
  // magic items state
  const [item, setItem] = useState<MagicItem | null>(null);
  const [busyItem, setBusyItem] = useState(false);
  const [itemLib, setItemLib] = useState<{id:number; name:string; created_at:string}[] | null>(null);
  const [busyItemLib, setBusyItemLib] = useState(false);
  const [itemPage, setItemPage] = useState(1);
  const itemPageSize = 8;
  const [itemTotal, setItemTotal] = useState(0);
  const [itemSearch, setItemSearch] = useState("");
  const [itemSort, setItemSort] = useState("created_desc");

  // spells state
  const [spell, setSpell] = useState<Spell | null>(null);
  const [busySpell, setBusySpell] = useState(false);
  const [spellLib, setSpellLib] = useState<{id:number; name:string; created_at:string}[] | null>(null);
  const [busySpellLib, setBusySpellLib] = useState(false);
  const [spellPage, setSpellPage] = useState(1);
  const spellPageSize = 8;
  const [spellTotal, setSpellTotal] = useState(0);
  const [spellSearch, setSpellSearch] = useState("");
  const [spellSort, setSpellSort] = useState("created_desc");
  const [progPlan, setProgPlan] = useState<import('./api').ProgressionPlan | null>(null);

  const [classMap, setClassMap] = useState<Record<string,string>>({});
  const [raceMap, setRaceMap]   = useState<Record<string,string>>({});
  const [bgMap, setBgMap]       = useState<Record<string,string>>({});
  // creation left-panel tabs
  const [createTab, setCreateTab] = useState<'pick'|'prog'|'story'>("pick");

  function withName(d: CharacterDraft): CharacterDraft {
    const cleaned = charName.trim();
    return { ...d, name: cleaned || d.name || null };
  }

  async function doSave() {
    if (!draft) return;
    const namedDraft = withName(draft);
    setDraft(namedDraft);
    const res = await saveToLibrary(namedDraft, backstory, portraitBase64 ?? null, progPlan ?? null);
    // refresh list after save
    await doListLib();
    // notify via toast if available (provider installed)
    try { const { useToast } = await import('./components/Toast'); useToast().push(`Saved #${res.id}: ${res.name}`, 'success'); } catch {}
  }

  async function doListLib() {
    setBusyLib(true);
    try {
      const res = await listLibrary(charPageSize, charPage, charSearch, charSort);
      setLib(res.items); setCharTotal(res.total);
    } finally {
      setBusyLib(false);
    }
  }

  async function doLoad(id: number) {
    const res = await getLibraryItem(id);
    const loadedDraft: CharacterDraft = {
      ...res.draft,
      name: res.draft.name ?? res.name ?? null,
    };
    setDraft(loadedDraft);
    setBackstory(res.backstory);
    setProgPlan((res as any).progression ?? null);
    setCharName(loadedDraft.name ?? "");
    if (res.portrait_base64) {
      setPortraitBase64(res.portrait_base64);
      try { if (portraitUrl) URL.revokeObjectURL(portraitUrl); } catch {}
      const blob = await (async()=>{ const b = atob(res.portrait_base64!); const arr = new Uint8Array(b.length); for(let i=0;i<b.length;i++)arr[i]=b.charCodeAt(i); return new Blob([arr], {type:"image/png"}); })();
      setPortraitUrl(URL.createObjectURL(blob));
    } else { setPortraitBase64(null); if (portraitUrl) { URL.revokeObjectURL(portraitUrl); setPortraitUrl(null);} }

    // Align pickers using name→index maps
    setSelectedClass(classMap[loadedDraft.cls.toLowerCase()] ?? "");
    setSelectedRace(raceMap[loadedDraft.race.toLowerCase()] ?? "");
    setSelectedBackground(bgMap[loadedDraft.background.toLowerCase()] ?? "");

    setLevel(loadedDraft.level);

    // Load ability scores from draft
    if (loadedDraft.abilities) {
      const abilityScores: Record<string, number> = {
        STR: loadedDraft.abilities.STR,
        DEX: loadedDraft.abilities.DEX,
        CON: loadedDraft.abilities.CON,
        INT: loadedDraft.abilities.INT,
        WIS: loadedDraft.abilities.WIS,
        CHA: loadedDraft.abilities.CHA,
      };
      // Sort scores in descending order
      const sortedScores = Object.values(abilityScores).sort((a, b) => b - a);
      // Create AbilitySet
      const abilitySet: AbilitySet = {
        method: "loaded",
        scores: sortedScores,
        rolls: [],
      };
      setAbilities(abilitySet);
      
      // Determine assignment: map sorted scores back to their abilities
      const used = new Set<string>();
      const assignment: Ability[] = [];
      for (const score of sortedScores) {
        // Find which ability has this score (handle duplicates by using first unused match)
        for (const [abil, val] of Object.entries(abilityScores)) {
          if (val === score && !used.has(abil)) {
            assignment.push(abil as Ability);
            used.add(abil);
            break;
          }
        }
      }
      setAssignment(assignment);
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function doDelete(id: number) {
    await deleteLibraryItem(id);
    await doListLib();
    if (draft && draft.name) setDraft(null);
  }
  function doCloseChar() { setDraft(null); setBackstory(null); setCharName(""); setPortraitBase64(null); if (portraitUrl) { try{ URL.revokeObjectURL(portraitUrl);}catch{}; setPortraitUrl(null); } setProgPlan(null); }
  
  // Reset all state when navigating to a creation page
  function resetToNewCreation() {
    // Character state
    setSelectedClass("");
    setSelectedRace("");
    setSelectedBackground("");
    setLevel(1);
    setAbilities(null);
    setSeed("");
    setAssignment(["STR","DEX","CON","INT","WIS","CHA"]);
    setDraft(null);
    setCharName("");
    setBackstory(null);
    setPortraitBase64(null);
    if (portraitUrl) { try{ URL.revokeObjectURL(portraitUrl);}catch{}; setPortraitUrl(null); }
    setProgPlan(null);
    setCreateTab("pick");
    // Magic item state
    setItem(null);
    // Spell state
    setSpell(null);
  }

  // Magic item library helpers
  async function doListItemLib() {
    setBusyItemLib(true);
    try { const res = await listMagicItems(itemPageSize, itemPage, itemSearch, itemSort); setItemLib(res.items); setItemTotal(res.total); }
    finally { setBusyItemLib(false); }
  }
  async function doLoadItem(id:number) { const res = await getMagicItem(id); setItem(res.item); }
  async function doDeleteItem(id:number) { await deleteMagicItem(id); await doListItemLib(); if (item && item.name) setItem(null); }
  function doCloseItem() { setItem(null); }

  // spell lib helpers
  async function doListSpellLib(){ setBusySpellLib(true); try { const res = await listSpells(spellPageSize, spellPage, spellSearch, spellSort); setSpellLib(res.items); setSpellTotal(res.total);} finally { setBusySpellLib(false);} }
  async function doLoadSpell(id:number){ const res = await getSpell(id); setSpell(res.spell); }
  async function doDeleteSpell(id:number){ await deleteSpell(id); await doListSpellLib(); if (spell && spell.name) setSpell(null); }
  function doCloseSpell() { setSpell(null); }

  // progression is attached to character draft now; no separate library


  useEffect(() => {
    fetch(`http://localhost:${import.meta.env.VITE_API_PORT ?? 8000}/health`)
      .then((r) => setApiOk(r.ok))
      .catch(() => setApiOk(false));
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const mapByName = (arr: APIRef[]) =>
          arr.reduce<Record<string,string>>((m, x) => { m[x.name.toLowerCase()] = x.index; return m; }, {});

        const [cls, rcs, bgs] = await Promise.all([listClasses(), listRaces(), listBackgrounds()]);
        setClasses(cls); setRaces(rcs); setBackgrounds(bgs);
        setClassMap(mapByName(cls));
        setRaceMap(mapByName(rcs));
        setBgMap(mapByName(bgs));

      } catch {
        setClasses([]); setRaces([]); setBackgrounds([]);
      }
    })();
  }, []);

  // auto-load lists when visiting libraries
  useEffect(() => {
    if (section === "char-lib") doListLib();
    if (section === "item-lib") doListItemLib();
    if (section === "spell-lib") doListSpellLib();
    // progression library removed
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section]);

  // Debounced library refresh when filters change
  useEffect(() => {
    if (section !== 'char-lib') return;
    const t = setTimeout(() => { doListLib(); updateUrl(); }, 300);
    return () => clearTimeout(t);
  }, [charPage, charSearch, charSort]);
  useEffect(() => {
    if (section !== 'item-lib') return;
    const t = setTimeout(() => { doListItemLib(); updateUrl(); }, 300);
    return () => clearTimeout(t);
  }, [itemPage, itemSearch, itemSort]);
  useEffect(() => {
    if (section !== 'spell-lib') return; const t = setTimeout(()=>{ doListSpellLib(); updateUrl(); }, 300); return ()=>clearTimeout(t);
  }, [spellPage, spellSearch, spellSort]);
  // removed: progression library debounce

  // URL state (section, pages, search, sort)
  useEffect(() => {
    const p = new URLSearchParams(location.search);
    const sec = p.get('sec') as typeof section | null;
    if (sec && (sec === "home" || sec === "char-new" || sec === "char-lib" || sec === "item-new" || sec === "item-lib" || sec === "spell-new" || sec === "spell-lib")) {
      setSection(sec);
    }
    const cp = Number(p.get('cp')||'1'); if (cp) setCharPage(cp);
    const cs = p.get('cs')||''; if (cs) setCharSearch(cs);
    const co = p.get('co')||''; if (co) setCharSort(co as any);
    const ip = Number(p.get('ip')||'1'); if (ip) setItemPage(ip);
    const is = p.get('is')||''; if (is) setItemSearch(is);
    const io = p.get('io')||''; if (io) setItemSort(io as any);
    const sp = Number(p.get('sp')||'1'); if (sp) setSpellPage(sp);
    const ss = p.get('ss')||''; if (ss) setSpellSearch(ss);
    const so = p.get('so')||''; if (so) setSpellSort(so as any);
    // progression list params removed
    // initial lists
    if (sec === 'char-lib') doListLib();
    if (sec === 'item-lib') doListItemLib();
    if (sec === 'spell-lib') doListSpellLib();
    // no progression library
    // If no section in URL, default to home
    if (!sec) {
      setSection("home");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateUrl(){
    const p = new URLSearchParams(location.search);
    p.set('sec', section);
    p.set('cp', String(charPage)); p.set('cs', charSearch); p.set('co', charSort);
    p.set('ip', String(itemPage)); p.set('is', itemSearch); p.set('io', itemSort);
    p.set('sp', String(spellPage)); p.set('ss', spellSearch); p.set('so', spellSort);
    // progression list params removed
    history.replaceState(null, '', `${location.pathname}?${p.toString()}`);
  }

  const canRoll = useMemo(() => !!selectedClass && !!selectedRace && !!selectedBackground, [selectedClass, selectedRace, selectedBackground]);
  const canGenerate = useMemo(() => !!abilities && canRoll && assignment.length === 6, [abilities, canRoll, assignment]);

  async function doRoll() {
    const s = seed.trim() === "" ? undefined : Number(seed);
    const data = await rollAbilities(s);
    setAbilities(data);
    setAssignment(["STR","DEX","CON","INT","WIS","CHA"]);
    setDraft(null);
    setBackstory(null);
    setCharName("");
    setPortraitBase64(null);
    if (portraitUrl) { try{ URL.revokeObjectURL(portraitUrl);}catch{}; setPortraitUrl(null); }
  }
  //function scoreFor(i: number){ return abilities ? abilities.scores[i] : 10; }

  async function doGenerate() {
    if (!abilities) return;
    try {
      setBusy(true);
      const payload = {
        class_index: selectedClass,
        race_index: selectedRace,
        background_index: selectedBackground,
        level,
        scores: abilities.scores,
        assignment,
      };
      const res = await generateDraft(payload);
      const defaultName = `${selectedRace || "Race"} ${selectedClass || "Class"}`.replace(/\b\w/g, (c) => c.toUpperCase());
      const nextDraft = { ...res, name: res.name ?? defaultName };
      setDraft(nextDraft);
      setCharName(nextDraft.name ?? "");
      setBackstory(null);
      setPortraitBase64(null);
      if (portraitUrl) { try{ URL.revokeObjectURL(portraitUrl);}catch{}; setPortraitUrl(null); }
    } finally { setBusy(false); }
  }

  async function doBackstory() {
    if (!draft) return;
    try {
      setBusyBS(true);
      const namedDraft = withName(draft);
      setDraft(namedDraft);
      const result = await generateBackstory({
        name: namedDraft.name ?? null,
        tone,
        length: lengthOpt,
        include_hooks: includeHooks,
        custom_inspiration: tone === "custom" && customInspiration.trim() ? customInspiration.trim() : null,
        draft: namedDraft,
      }, engine);
      setBackstory(result);
      try { const { useToast } = await import('./components/Toast'); useToast().push('Backstory ready', 'success'); } catch {}
    } finally { setBusyBS(false); }
  }

  async function doQuickNPC() {
    if (!classes || !races || !backgrounds) return;

    // 1) pick random class/race/background
    const c = randPick(classes);
    const r = randPick(races);
    const b = randPick(backgrounds);

    setSelectedClass(c.index);
    setSelectedRace(r.index);
    setSelectedBackground(b.index);

    // 2) roll abilities (seeded for reproducibility)
    const seedVal = Math.floor(Math.random() * 1_000_000);
    setSeed(String(seedVal));
    const rolled = await rollAbilities(seedVal);
    setAbilities(rolled);

    // 3) auto-assign by class priorities
    const auto = autoAssignmentForClass(c.index);
    setAssignment(auto);

    // 4) generate draft
    setBusy(true);
    try {
      const res = await generateDraft({
        class_index: c.index,
        race_index: r.index,
        background_index: b.index,
        level,
        scores: rolled.scores,
        assignment: auto,
      });
      const quickName = `${r.name} ${c.name}`.replace(/\b\w/g, (ch) => ch.toUpperCase());
      const nextDraft = { ...res, name: res.name ?? quickName };
      setDraft(nextDraft);
      setCharName(nextDraft.name ?? "");
      setBackstory(null);
      setPortraitBase64(null);
      if (portraitUrl) { try{ URL.revokeObjectURL(portraitUrl);}catch{}; setPortraitUrl(null); }

      // 5) optional quick backstory (short, heroic)
      if (GOOGLE_KEY_PRESENT) {
        const bs = await generateBackstory({
          name: nextDraft.name ?? null,
          tone: "heroic",
          length: "short",
          include_hooks: true,
          draft: nextDraft,
        });
        setBackstory(bs);
      }
    } finally {
      setBusy(false);
    }
  }

  async function doPortrait() {
    if (!draft) return;
    const namedDraft = withName(draft);
    const blob = await generatePortrait(namedDraft, backstory, engine);
    const url = URL.createObjectURL(blob);
    setPortraitUrl(url);
    // also hold base64 for saving/export
    const arrayBuffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);
    let binary = ""; for (let i=0;i<bytes.length;i++) binary += String.fromCharCode(bytes[i]);
    setPortraitBase64(btoa(binary));
    try { const { useToast } = await import('./components/Toast'); useToast().push('Portrait generated', 'success'); } catch {}
  }

  // Magic item generation/save
  async function doGenerateItem(input: { name?: string; item_type?: string; rarity?: string; requires_attunement?: boolean; prompt?: string }) {
    try { setBusyItem(true); const it = await generateMagicItem(input, engine); setItem(it); }
    finally { setBusyItem(false); }
  }
  async function doSaveItem() { if (!item) return; const res = await saveMagicItem(item); await doListItemLib(); try { const { useToast } = await import('./components/Toast'); useToast().push(`Saved Item #${res.id}: ${res.name}`, 'success'); } catch {} }

  const [navExpanded, setNavExpanded] = useState(true);
  const [engine, setEngine] = useState<'google'|'local'>(()=> (localStorage.getItem('engine') as any) || 'google');
  useEffect(()=>{ localStorage.setItem('engine', engine); }, [engine]);

  return (
    <div className="min-h-screen app-bg text-slate-100 flex">
      <Sidebar expanded={navExpanded} setExpanded={setNavExpanded} section={section} onSelect={setSection} apiOk={apiOk} engine={engine} setEngine={setEngine} />
      <div className="p-6 flex-1">
        {section === "home" && (
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl font-bold mb-8 text-center">Welcome to the Forge</h1>
            <div className="grid gap-6 md:grid-cols-3">
              <GlassCard 
                className="cursor-pointer hover:bg-white/10 transition-colors text-center py-8"
                onClick={() => { resetToNewCreation(); setSection("char-new"); }}
              >
                <h2 className="text-2xl font-semibold">New Character</h2>
              </GlassCard>
              <GlassCard 
                className="cursor-pointer hover:bg-white/10 transition-colors text-center py-8"
                onClick={() => { resetToNewCreation(); setSection("item-new"); }}
              >
                <h2 className="text-2xl font-semibold">New Magic Item</h2>
              </GlassCard>
              <GlassCard 
                className="cursor-pointer hover:bg-white/10 transition-colors text-center py-8"
                onClick={() => { resetToNewCreation(); setSection("spell-new"); }}
              >
                <h2 className="text-2xl font-semibold">New Spell</h2>
              </GlassCard>
            </div>
          </div>
        )}
        {section === "char-new" && (
          <div className="grid gap-6 md:grid-cols-2 fill-grid">
            <div className="card-flex">
              <GlassCard className="mb-3">
                <Tabs
                  tabs={[{key:'pick',label:'Pick & Abilities'},{key:'story',label:'Backstory'},{key:'prog',label:'Progression'}]}
                  active={createTab}
                  onChange={(k)=>setCreateTab(k as any)}
                />
              </GlassCard>
              <div className="flex-scroll">
                {createTab === 'pick' && (
                  <div className="grid gap-6">
                    <GlassCard>
                      <h2 className="text-xl font-semibold mb-2">Pick Class, Race, Background</h2>
                      <PickersPanel
                        classes={classes}
                        races={races}
                        backgrounds={backgrounds}
                        selectedClass={selectedClass}
                        selectedRace={selectedRace}
                        selectedBackground={selectedBackground}
                        setSelectedClass={setSelectedClass}
                        setSelectedRace={setSelectedRace}
                        setSelectedBackground={setSelectedBackground}
                        seed={seed}
                        setSeed={setSeed}
                        canRoll={canRoll}
                        doRoll={doRoll}
                        level={level}
                        setLevel={(n)=>setLevel(n)}
                        onQuickNPC={doQuickNPC}
                      />
                    </GlassCard>
                    <GlassCard>
                      <h2 className="text-xl font-semibold mb-2">Ability Scores</h2>
                      <AbilitiesPanel
                        abilities={abilities}
                        assignment={assignment}
                        setAssignment={setAssignment}
                        canGenerate={canGenerate}
                        busy={busy}
                        doGenerate={doGenerate}
                      />
                    </GlassCard>
                  </div>
                )}
                {createTab === 'prog' && (
                  <div>
                    {/* ProgressionPanel already includes its own frosted GlassCard */}
                    <ProgressionPanel draft={draft} classIndex={selectedClass || null} plan={progPlan} setPlan={setProgPlan} />
                  </div>
                )}
                {createTab === 'story' && (
                  <div style={{height:'100%'}}>
                    <GlassCard className="fill-card">
                      <h2 className="text-xl font-semibold mb-2">Backstory</h2>
                      <BackstoryPanel
                        draft={draft}
                        tone={tone}
                        setTone={setTone}
                        lengthOpt={lengthOpt}
                        setLengthOpt={setLengthOpt}
                        includeHooks={includeHooks}
                        setIncludeHooks={setIncludeHooks}
                        customInspiration={customInspiration}
                        setCustomInspiration={setCustomInspiration}
                        busyBS={busyBS}
                        doBackstory={doBackstory}
                        backstory={backstory}
                      />
                    </GlassCard>
                  </div>
                )}
              </div>
            </div>
            <GlassCard>
              <h2 className="text-xl font-semibold mb-3">Draft Sheet</h2>
              {!draft ? (
                <p className="text-slate-300">No draft yet.</p>
              ) : (
                <GlassCard>
                  <DraftPanel
                    draft={withName(draft)}
                    backstory={backstory}
                    charName={charName}
                    setCharName={setCharName}
                    downloadJSON={(d,b)=>downloadJSON(d,b,progPlan)}
                    downloadMarkdown={(d,b)=>downloadMarkdown(d,b,progPlan)}
                    doSave={doSave}
                    portraitUrl={portraitUrl}
                    onGeneratePortrait={doPortrait}
                    onDownloadPDF={()=>downloadPDF(withName(draft), backstory, portraitBase64, progPlan)}
                  />
                </GlassCard>
              )}
            </GlassCard>
          </div>
        )}

        {section === "item-new" && (
          <div className="grid gap-6 md:grid-cols-2 fill-grid">
            <div className="card-flex">
              <GlassCard className="mb-3">
                <h2 className="text-xl font-semibold mb-3">Create New Magic Item</h2>
              </GlassCard>
              <div className="flex-scroll">
                <GlassCard>
                  <MagicItemForm onGenerate={doGenerateItem} busy={busyItem} />
                </GlassCard>
              </div>
            </div>
            <GlassCard>
              <h2 className="text-xl font-semibold mb-3">Preview</h2>
              {!item ? (
                <p className="text-slate-300">No item generated yet.</p>
              ) : (
                <GlassCard>
                  <MagicItemPreview item={item} onSave={doSaveItem} />
                </GlassCard>
              )}
            </GlassCard>
          </div>
        )}
        {section === "spell-new" && (
          <div className="grid gap-6 md:grid-cols-1">
            <GlassCard>
              <h2 className="text-xl font-semibold mb-3">Create New Spell</h2>
              <SpellForm onGenerate={async (input)=>{ try{ setBusySpell(true); const sp = await generateSpell(input, engine); setSpell(sp);} finally{ setBusySpell(false);} }} busy={busySpell} />
            </GlassCard>
            <GlassCard>
              <h2 className="text-xl font-semibold mb-3">Preview</h2>
              <SpellPreview spell={spell} onSave={async ()=>{ if(!spell) return; await saveSpell(spell); await doListSpellLib(); }} />
            </GlassCard>
          </div>
        )}
        {section === "char-lib" && (
          <div className={`grid gap-6 ${draft ? "md:grid-cols-2 fill-grid" : "md:grid-cols-1"}`}>
            <GlassCard>
              <CharLibraryTable
                rows={lib}
                total={charTotal}
                page={charPage}
                pageSize={charPageSize}
                search={charSearch}
                sort={charSort}
                busy={busyLib}
                onRefresh={doListLib}
                onSelect={doLoad}
                onDelete={doDelete}
                onPageChange={(p)=>{ setCharPage(p); doListLib(); }}
                onSearchChange={(q)=>{ setCharSearch(q); setCharPage(1); doListLib(); }}
                onSortChange={(s)=>{ setCharSort(s); setCharPage(1); doListLib(); }}
                twoPanelMode={!!draft}
              />
            </GlassCard>
            {draft && (
              <GlassCard>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xl font-semibold">Preview</h2>
                  <LoadingButton onClick={doCloseChar}>Close</LoadingButton>
                </div>
                <GlassCard>
                  <DraftPanel
                    draft={withName(draft)}
                    backstory={backstory}
                    charName={charName}
                    setCharName={setCharName}
                    downloadJSON={(d,b)=>downloadJSON(d,b,progPlan)}
                    downloadMarkdown={(d,b)=>downloadMarkdown(d,b,progPlan)}
                    doSave={doSave}
                    portraitUrl={portraitUrl}
                    onGeneratePortrait={doPortrait}
                    onDownloadPDF={()=>downloadPDF(withName(draft), backstory, portraitBase64, progPlan)}
                  />
                </GlassCard>
              </GlassCard>
            )}
          </div>
        )}
        {/* Removed standalone progression sections; integrated above */}
        {section === "item-lib" && (
          <div className={`grid gap-6 ${item ? "md:grid-cols-2 fill-grid" : "md:grid-cols-1"}`}>
            <GlassCard>
              <ItemLibraryTable
                rows={itemLib}
                total={itemTotal}
                page={itemPage}
                pageSize={itemPageSize}
                search={itemSearch}
                sort={itemSort}
                busy={busyItemLib}
                onRefresh={doListItemLib}
                onSelect={doLoadItem}
                onDelete={doDeleteItem}
                onPageChange={(p)=>{ setItemPage(p); doListItemLib(); }}
                onSearchChange={(q)=>{ setItemSearch(q); setItemPage(1); doListItemLib(); }}
                onSortChange={(s)=>{ setItemSort(s); setItemPage(1); doListItemLib(); }}
                twoPanelMode={!!item}
              />
            </GlassCard>
            {item && (
              <GlassCard>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xl font-semibold">Preview</h2>
                  <LoadingButton onClick={doCloseItem}>Close</LoadingButton>
                </div>
                <GlassCard>
                  <MagicItemPreview item={item} onSave={()=>{}} />
                </GlassCard>
              </GlassCard>
            )}
          </div>
        )}
        {section === "spell-lib" && (
          <div className={`grid gap-6 ${spell ? "md:grid-cols-2 fill-grid" : "md:grid-cols-1"}`}>
            <GlassCard>
              <SpellLibraryTable
                rows={spellLib}
                total={spellTotal}
                page={spellPage}
                pageSize={spellPageSize}
                search={spellSearch}
                sort={spellSort}
                busy={busySpellLib}
                onRefresh={doListSpellLib}
                onSelect={doLoadSpell}
                onDelete={doDeleteSpell}
                onPageChange={(p)=>{ setSpellPage(p); doListSpellLib(); }}
                onSearchChange={(q)=>{ setSpellSearch(q); setSpellPage(1); doListSpellLib(); }}
                onSortChange={(s)=>{ setSpellSort(s); setSpellPage(1); doListSpellLib(); }}
                twoPanelMode={!!spell}
              />
            </GlassCard>
            {spell && (
              <GlassCard>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-xl font-semibold">Preview</h2>
                  <LoadingButton onClick={doCloseSpell}>Close</LoadingButton>
                </div>
                <GlassCard>
                  <SpellPreview spell={spell} onSave={()=>{}} />
                </GlassCard>
              </GlassCard>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// moved GlassCard to components
