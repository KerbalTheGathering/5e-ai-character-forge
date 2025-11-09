import type { Spell } from '../api';
import { downloadSpellJSON, downloadSpellMarkdown } from '../api';
import LoadingButton from "./LoadingButton";

export default function SpellPreview({ spell, onSave }: { spell: Spell | null; onSave: ()=>void | Promise<void> }){
  if (!spell) return <p className="text-slate-300">No spell generated yet.</p>;
  return (
    <div className="card-flex" style={{minHeight: 280}}>
      {/* Middle: spell details (scrollable) */}
      <div className="flex-scroll text-sm">
        <div className="mb-2">
          <div className="text-xl font-semibold mb-1"><strong>{spell.name}</strong></div>
          <div className="text-sm text-slate-300">Level {spell.level===0? 'Cantrip': spell.level} {spell.school}</div>
        </div>
        <div className="mb-2 text-sm">Classes: {spell.classes.join(', ') || '—'}</div>
        <div className="mb-2 text-sm">Casting Time: {spell.casting_time} · Range: {spell.range} · Duration: {spell.duration}</div>
        <div className="mb-2 text-sm">Components: {spell.components} · Concentration: {spell.concentration? 'Yes':'No'} · Ritual: {spell.ritual? 'Yes':'No'}</div>
        <div className="mb-2 whitespace-pre-wrap text-sm" style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>{spell.description}</div>
        {spell.damage && <div className="mb-2 text-sm"><strong>Damage:</strong> {spell.damage}</div>}
        {spell.save && <div className="mb-2 text-sm"><strong>Save:</strong> {spell.save}</div>}
      </div>

      {/* Bottom: actions anchored right */}
      <div className="card-actions">
        <LoadingButton onClick={()=>downloadSpellJSON(spell)}>Download JSON</LoadingButton>
        <LoadingButton onClick={()=>downloadSpellMarkdown(spell)}>Download Markdown</LoadingButton>
        <LoadingButton onClick={onSave}>Save to Library</LoadingButton>
      </div>
    </div>
  );
}
