import type { APIRef } from "../types";

export default function PickersPanel({
  classes, races, backgrounds,
  selectedClass, selectedRace, selectedBackground,
  setSelectedClass, setSelectedRace, setSelectedBackground,
  seed, setSeed, canRoll, doRoll,
  level, setLevel, onQuickNPC,
}: {
  classes: APIRef[] | null;
  races: APIRef[] | null;
  backgrounds: APIRef[] | null;
  selectedClass: string;
  selectedRace: string;
  selectedBackground: string;
  setSelectedClass: (v: string)=>void;
  setSelectedRace: (v: string)=>void;
  setSelectedBackground: (v: string)=>void;
  seed: string;
  setSeed: (v: string)=>void;
  canRoll: boolean;
  doRoll: ()=>void;
  level: number;
  setLevel: (n: number)=>void;
  onQuickNPC: ()=>void;
}) {
  return (
    <div className="card-flex">
      <div className="flex items-center justify-between mb-3">
        <button onClick={onQuickNPC} className="btn">🎲 Quick NPC</button>
        <div style={{display:'flex', alignItems:'center', gap:'.5rem'}}>
          <label className="text-sm">Level</label>
          <input type="number" min={1} max={20} value={level} onChange={(e)=>setLevel(Math.max(1, Math.min(20, Number(e.target.value)||1)))} className="glass-input" style={{width:'5.5rem'}} />
        </div>
      </div>

      <label className="block text-sm mb-1">Class</label>
      <select className="glass-input mb-3" value={selectedClass} onChange={(e)=>setSelectedClass(e.target.value)}>
        <option value="">— choose —</option>
        {classes?.map(c=> <option key={c.index} value={c.index}>{c.name}</option>)}
      </select>

      <label className="block text-sm mb-1">Race</label>
      <select className="glass-input mb-3" value={selectedRace} onChange={(e)=>setSelectedRace(e.target.value)}>
        <option value="">— choose —</option>
        {races?.map(r=> <option key={r.index} value={r.index}>{r.name}</option>)}
      </select>

      <label className="block text-sm mb-1">Background</label>
      <select className="glass-input mb-3" value={selectedBackground} onChange={(e)=>setSelectedBackground(e.target.value)}>
        <option value="">— choose —</option>
        {backgrounds?.map(b=> <option key={b.index} value={b.index}>{b.name}</option>)}
      </select>

      <label className="block text-sm mb-1">Seed (optional)</label>
      <input className="glass-input mb-2" placeholder="e.g. 42" value={seed} onChange={(e)=>setSeed(e.target.value.replace(/[^\d]/g,""))}/>
      <div className="card-actions">
        <button disabled={!canRoll} onClick={doRoll} className={`btn ${canRoll ? "" : "btn-disabled"}`}>Roll 4d6 drop-lowest</button>
      </div>
    </div>
  );
}
