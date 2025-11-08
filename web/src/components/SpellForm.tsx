import { useState } from 'react';
import LoadingButton from './LoadingButton';

export default function SpellForm({ onGenerate, busy }: { onGenerate:(input:{ name?:string; level?:number; school?:string; classes?:string[]; target?:string; intent?:string; prompt?:string; })=>void|Promise<void>; busy:boolean }){
  const [name,setName] = useState('');
  const [level,setLevel] = useState(1);
  const [school,setSchool] = useState('Evocation');
  const [classes,setClasses] = useState('Wizard, Sorcerer');
  const [target,setTarget] = useState('one');
  const [intent,setIntent] = useState('damage');
  const [prompt,setPrompt] = useState('');

  return (
    <div className="card-flex">
      <div className="grid gap-2" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}>
        <div>
          <label className="block text-sm mb-1">Name (optional)</label>
          <input className="glass-input" value={name} onChange={e=>setName(e.target.value)} placeholder="e.g., Cubelet’s Glide"/>
        </div>
        <div>
          <label className="block text-sm mb-1">Level</label>
          <select className="glass-input" value={level} onChange={e=>setLevel(Number(e.target.value))}>
            {[0,1,2,3,4,5,6,7,8,9].map(n=> <option key={n} value={n}>{n===0? 'Cantrip': n}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">School</label>
          <select className="glass-input" value={school} onChange={e=>setSchool(e.target.value)}>
            {['Abjuration','Conjuration','Divination','Enchantment','Evocation','Illusion','Necromancy','Transmutation'].map(s=> <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Classes</label>
          <input className="glass-input" value={classes} onChange={e=>setClasses(e.target.value)} placeholder="comma-separated"/>
        </div>
        <div>
          <label className="block text-sm mb-1">Target</label>
          <select className="glass-input" value={target} onChange={e=>setTarget(e.target.value)}>
            <option>one</option><option>multiple</option><option>self</option><option>area</option>
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1">Intent</label>
          <select className="glass-input" value={intent} onChange={e=>setIntent(e.target.value)}>
            <option>damage</option><option>healing</option><option>utility</option><option>control</option>
          </select>
        </div>
      </div>
      <div className="mt-3">
        <label className="block text-sm mb-1">Prompt (optional)</label>
        <textarea className="glass-input" rows={6} placeholder="Theme, constraints, lore..." value={prompt} onChange={e=>setPrompt(e.target.value)} />
      </div>
      <div className="card-actions">
        <LoadingButton loading={busy} onClick={()=>onGenerate({ name: name||undefined, level, school, classes: classes.split(',').map(s=>s.trim()).filter(Boolean), target, intent, prompt })}>
          Generate Spell
        </LoadingButton>
      </div>
    </div>
  );
}
