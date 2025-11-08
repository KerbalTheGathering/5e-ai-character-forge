import { useState } from "react";
import type { MagicItem } from "../api";

export default function MagicItemForm({
  onGenerate,
  busy,
}: {
  onGenerate: (input: { name?: string; item_type?: string; rarity?: string; requires_attunement?: boolean; prompt?: string })=>void | Promise<void>;
  busy: boolean;
}){
  const [name, setName] = useState("");
  const [itemType, setItemType] = useState("Wondrous item");
  const [rarity, setRarity] = useState("Uncommon");
  const [attune, setAttune] = useState(false);
  const [prompt, setPrompt] = useState("");

  return (
    <div className="card-flex">
      <div className="grid gap-2" style={{gridTemplateColumns:"repeat(2,minmax(0,1fr))"}}>
        <div>
          <label className="block text-sm mb-1">Item Name (optional)</label>
          <input className="glass-input" placeholder="e.g., Emberheart Talisman" value={name} onChange={(e)=>setName(e.target.value)} />
        </div>
        <div>
          <label className="block text-sm mb-1">Type</label>
          <select className="glass-input" value={itemType} onChange={(e)=>setItemType(e.target.value)}>
            {['Wondrous item','Weapon','Armor','Ring','Rod','Staff','Wand','Scroll','Potion','Ammunition','Instrument'].map(t=> <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Rarity</label>
          <select className="glass-input" value={rarity} onChange={(e)=>setRarity(e.target.value)}>
            {['Common','Uncommon','Rare','Very Rare','Legendary'].map(r=> <option key={r}>{r}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <label className="text-sm">
            <input type="checkbox" className="mr-2" checked={attune} onChange={(e)=>setAttune(e.target.checked)} /> Requires Attunement
          </label>
        </div>
      </div>
      <div className="mt-3">
        <label className="block text-sm mb-1">Prompt (optional)</label>
        <textarea className="glass-input" rows={6} placeholder="Theme, lore, constraints, mechanics..." value={prompt} onChange={(e)=>setPrompt(e.target.value)} />
      </div>
      <div className="card-actions">
        <button className={`btn ${busy ? 'btn-disabled':''}`} onClick={()=>onGenerate({ name, item_type: itemType, rarity, requires_attunement: attune, prompt })}>
          {busy ? 'Generating…' : 'Generate Item'}
        </button>
      </div>
    </div>
  );
}
