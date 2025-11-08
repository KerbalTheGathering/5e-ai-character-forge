import type { APIRef } from "../types";
import LoadingButton from "./LoadingButton";

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
        <LoadingButton onClick={onQuickNPC}>🎲 Quick NPC</LoadingButton>
        <div style={{display:'flex', alignItems:'center', gap:'.5rem'}}>
          <label className="text-sm">Level</label>
          <input type="number" min={1} max={20} value={level} onChange={(e)=>setLevel(Math.max(1, Math.min(20, Number(e.target.value)||1)))} className="glass-input" style={{width:'5.5rem'}} />
        </div>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'repeat(2,minmax(0,1fr))', gap:'.75rem', columnGap:'1rem'}}>
        <div>
          <label className="block text-sm mb-1">Class</label>
          <select className="glass-input" value={selectedClass} onChange={(e)=>setSelectedClass(e.target.value)}>
            <option value="">— choose —</option>
            {classes?.map(c=> <option key={c.index} value={c.index}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Race</label>
          <select className="glass-input" value={selectedRace} onChange={(e)=>setSelectedRace(e.target.value)}>
            <option value="">— choose —</option>
            {races?.map(r=> <option key={r.index} value={r.index}>{r.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Background</label>
          <select className="glass-input" value={selectedBackground} onChange={(e)=>setSelectedBackground(e.target.value)}>
            <option value="">— choose —</option>
            {backgrounds?.map(b=> <option key={b.index} value={b.index}>{b.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Seed (optional)</label>
          <input className="glass-input" placeholder="e.g. 42" value={seed} onChange={(e)=>setSeed(e.target.value.replace(/[^\d]/g,""))}/>
        </div>
      </div>
      <div className="card-actions">
        <LoadingButton disabled={!canRoll} onClick={doRoll}>Roll 4d6 drop-lowest</LoadingButton>
      </div>
    </div>
  );
}
