import { useState } from 'react';
import GlassCard from './GlassCard';
import type { CharacterDraft } from '../api';
import { generateProgression, type ProgressionPlan, downloadProgressionMarkdown, downloadProgressionPDF } from '../api';

export default function ProgressionPanel({ draft, classIndex, plan: planProp, setPlan: setPlanProp }: { draft: CharacterDraft | null; classIndex: string | null; plan?: ProgressionPlan | null; setPlan?: (p:ProgressionPlan)=>void }) {
  const [target, setTarget] = useState<number>(draft?.level ?? 1);
  const [allowFeats, setAllowFeats] = useState(false);
  const [style, setStyle] = useState<'martial'|'caster'|'face'|'balanced'>('balanced');
  const [busy, setBusy] = useState(false);
  const [plan, setPlanLocal] = useState<ProgressionPlan | null>(null);
  const setPlan = (p: ProgressionPlan) => { setPlanProp ? setPlanProp(p) : setPlanLocal(p); };
  const planEffective = planProp ?? plan;

  async function onGenerate(){
    if (!draft || !classIndex) return;
    setBusy(true);
    try {
      const p = await generateProgression({ class_index: classIndex, target_level: target, allow_feats: allowFeats, style, draft });
      setPlan(p);
    } finally { setBusy(false); }
  }

  async function onExport(){ if (planEffective) await downloadProgressionMarkdown(planEffective); }
  async function onExportPDF(){ if (planEffective) await downloadProgressionPDF(planEffective); }
  function onAttach(){ if (planEffective && setPlanProp) setPlanProp(planEffective); }

  return (
    <GlassCard>
      <div className="card-flex">
      <h2 className="text-xl font-semibold mb-3">Level Progression Planner</h2>
      {!draft && (
        <div className="text-slate-300">Generate a character first to plan progression.</div>
      )}
      {draft && (
        <div className="flex-scroll">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <label>
              <div className="block text-sm mb-1">Target Level</div>
              <input className="glass-input" type="number" min={1} max={20} value={target} onChange={e=>setTarget(Math.max(1, Math.min(20, Number(e.target.value)||1)))} />
            </label>
            <label>
              <div className="block text-sm mb-1">Style</div>
              <select className="glass-input" value={style} onChange={e=>setStyle(e.target.value as any)}>
                <option value="balanced">Balanced</option>
                <option value="martial">Martial</option>
                <option value="caster">Caster</option>
                <option value="face">Face</option>
              </select>
            </label>
            <label className="flex items-center" style={{gap:'.5rem'}}>
              <input type="checkbox" checked={allowFeats} onChange={e=>setAllowFeats(e.target.checked)} /> Allow feats
            </label>
            <div>
              <button className="btn" onClick={onGenerate} disabled={busy || !classIndex}>{busy? 'Generating…':'Generate Plan'}</button>
            </div>
          </div>

          {planEffective && (
            <div style={{marginTop:'1rem'}}>
              <div className="flex" style={{gap:'.5rem'}}>
                <button className="btn" onClick={onAttach}>Save Progression into Character</button>
                <button className="btn" onClick={onExport}>Export Markdown</button>
                <button className="btn" onClick={onExportPDF}>Export PDF</button>
              </div>
              <div style={{marginTop:'1rem', overflowX:'auto'}}>
                <table className="lib-table">
                  <thead>
                    <tr>
                      <th style={{whiteSpace:'nowrap'}}>Level</th>
                      <th>Features</th>
                      <th style={{whiteSpace:'nowrap'}}>Subclass</th>
                      <th style={{whiteSpace:'nowrap'}}>ASI/Feat</th>
                      <th style={{whiteSpace:'nowrap'}}>HP Gain</th>
                    </tr>
                  </thead>
                  <tbody>
                    {planEffective.picks.map(p => (
                      <tr key={p.level}>
                        <td>{p.level}</td>
                        <td>{p.features && p.features.length ? p.features.join(', ') : '—'}</td>
                        <td>{p.subclass ?? '—'}</td>
                        <td>{p.asi ?? '—'}</td>
                        <td>{p.hp_gain ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {planEffective.notes_markdown && (
                <div style={{marginTop:'0.75rem'}}>
                  <div className="text-slate-300" style={{whiteSpace:'pre-wrap'}}>{planEffective.notes_markdown}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <div className="card-actions" />
      </div>
    </GlassCard>
  );
}
