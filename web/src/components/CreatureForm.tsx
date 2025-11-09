import { useState } from "react";
import LoadingButton from "./LoadingButton";

export default function CreatureForm({
  onGenerate,
  busy,
}: {
  onGenerate: (input: { name?: string; size?: string; creature_type?: string; challenge_rating?: string; base_stat_block?: string; prompt?: string })=>void | Promise<void>;
  busy: boolean;
}){
  const [name, setName] = useState("");
  const [size, setSize] = useState("Medium");
  const [creatureType, setCreatureType] = useState("Humanoid");
  const [cr, setCr] = useState("1");
  const [baseStat, setBaseStat] = useState("");
  const [prompt, setPrompt] = useState("");

  return (
    <div className="card-flex">
      <div className="grid gap-2" style={{gridTemplateColumns:"repeat(2,minmax(0,1fr))"}}>
        <div>
          <label className="block text-sm mb-1">Creature Name (optional)</label>
          <input className="glass-input" placeholder="e.g., Fire-Breathing Giant Toad" value={name} onChange={(e)=>setName(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm mb-1">Size</label>
          <select className="glass-input" value={size} onChange={(e)=>setSize(e.target.value)}>
            {['Tiny','Small','Medium','Large','Huge','Gargantuan'].map(s=> <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Creature Type</label>
          <select className="glass-input" value={creatureType} onChange={(e)=>setCreatureType(e.target.value)}>
            {['Humanoid','Beast','Undead','Fiend','Celestial','Elemental','Fey','Aberration','Construct','Dragon','Giant','Monstrosity','Ooze','Plant'].map(t=> <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Challenge Rating</label>
          <select className="glass-input" value={cr} onChange={(e)=>setCr(e.target.value)}>
            {['0','1/8','1/4','1/2','1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30'].map(c=> <option key={c}>{c}</option>)}
          </select>
        </div>
      </div>
      <div className="mt-3">
        <label className="block text-sm mb-1">Base Stat Block Reference (optional)</label>
        <input className="glass-input" placeholder="e.g., Ogre, Skeleton" value={baseStat} onChange={(e)=>setBaseStat(e.target.value)} />
      </div>
      <div className="mt-3">
        <label className="block text-sm mb-1">Prompt (optional)</label>
        <textarea className="glass-input" rows={6} placeholder="Theme, lore, constraints, mechanics..." value={prompt} onChange={(e)=>setPrompt(e.target.value)} />
      </div>
      <div className="card-actions">
        <LoadingButton loading={busy} onClick={()=>onGenerate({ name, size, creature_type: creatureType, challenge_rating: cr, base_stat_block: baseStat || undefined, prompt })}>
          Generate Creature
        </LoadingButton>
      </div>
    </div>
  );
}

