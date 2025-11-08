import type { Spell } from '../api';
import { downloadSpellJSON, downloadSpellMarkdown } from '../api';
import LoadingButton from "./LoadingButton";

export default function SpellPreview({ spell, onSave }: { spell: Spell | null; onSave: ()=>void | Promise<void> }){
  if (!spell) return <p className="text-slate-300">No spell generated yet.</p>;
  return (
    <div className="text-sm card-flex">
      <div>
        <div className="mb-2"><strong>{spell.name}</strong> — Level {spell.level===0? 'Cantrip': spell.level} {spell.school}</div>
        <div className="mb-2">Classes: {spell.classes.join(', ') || '—'}</div>
        <div className="mb-2">Casting Time: {spell.casting_time} · Range: {spell.range} · Duration: {spell.duration}</div>
        <div className="mb-2">Components: {spell.components} · Concentration: {spell.concentration? 'Yes':'No'} · Ritual: {spell.ritual? 'Yes':'No'}</div>
        <div className="mb-2 whitespace-pre-wrap">{spell.description}</div>
        {spell.damage && <div className="mb-2">Damage: {spell.damage}</div>}
        {spell.save && <div className="mb-2">Save: {spell.save}</div>}
      </div>
      <div className="card-actions">
        <LoadingButton className="mr-2" onClick={()=>downloadSpellJSON(spell)}>Download JSON</LoadingButton>
        <LoadingButton className="mr-2" onClick={()=>downloadSpellMarkdown(spell)}>Download Markdown</LoadingButton>
        <LoadingButton onClick={onSave}>Save to Library</LoadingButton>
      </div>
    </div>
  );
}
