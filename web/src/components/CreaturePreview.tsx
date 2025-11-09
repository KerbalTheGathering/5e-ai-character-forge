import { downloadCreatureJSON, downloadCreatureMarkdown, type Creature } from "../api";
import LoadingButton from "./LoadingButton";
import GlassCard from "./GlassCard";

export default function CreaturePreview({ 
  creature, 
  onSave, 
  portraitUrl, 
  onGeneratePortrait 
}: { 
  creature: Creature | null; 
  onSave: ()=>void | Promise<void>;
  portraitUrl?: string | null;
  onGeneratePortrait?: ()=>void | Promise<void>;
}){
  if (!creature) return <p className="text-slate-300">No creature generated yet.</p>;
  return (
    <div className="card-flex" style={{minHeight: 280}}>
      {/* Middle: details left, portrait right (wrapped in frosted glass card) */}
      <GlassCard className="flex-scroll">
        <div className="draft-grid">
          <div className="draft-left text-sm">
            <div className="mb-2">
              <div className="text-xl font-semibold mb-1">{creature.name}</div>
              <div className="text-sm text-slate-300">{creature.size} {creature.creature_type} · Challenge Rating {creature.challenge_rating}</div>
            </div>
            <div className="mb-2">
              <div className="text-sm"><strong>Armor Class:</strong> {creature.armor_class}</div>
              <div className="text-sm"><strong>Hit Points:</strong> {creature.hit_points} ({creature.hit_dice})</div>
              <div className="text-sm"><strong>Speed:</strong> {creature.speed}</div>
            </div>
            {/* Abilities */}
            <div className="mb-2">
              <div className="text-slate-300 text-sm mb-1">Abilities</div>
              <div className="grid gap-2" style={{gridTemplateColumns: "repeat(3, minmax(0, 1fr))"}}>
                {([
                  ['STR', creature.ability_scores.STR, creature.ability_scores.STR_mod],
                  ['DEX', creature.ability_scores.DEX, creature.ability_scores.DEX_mod],
                  ['CON', creature.ability_scores.CON, creature.ability_scores.CON_mod],
                  ['INT', creature.ability_scores.INT, creature.ability_scores.INT_mod],
                  ['WIS', creature.ability_scores.WIS, creature.ability_scores.WIS_mod],
                  ['CHA', creature.ability_scores.CHA, creature.ability_scores.CHA_mod],
                ] as [string, number, number][]).map(([abbr, score, mod]) => (
                  <div key={abbr} className="bg-black/40 rounded border border-white/10 p-2 text-center">
                    <div className="text-xs text-slate-400">{abbr}</div>
                    <div className="text-lg font-semibold">{score}</div>
                    <div className="text-xs text-slate-300">{mod >= 0 ? `(+${mod})` : `(${mod})`}</div>
                  </div>
                ))}
              </div>
            </div>
            {creature.saving_throws?.length > 0 && (
              <div className="mb-2 text-sm"><strong>Saving Throws:</strong> {creature.saving_throws.join(", ")}</div>
            )}
            {creature.skills?.length > 0 && (
              <div className="mb-2 text-sm"><strong>Skills:</strong> {creature.skills.join(", ")}</div>
            )}
            {creature.damage_resistances?.length > 0 && (
              <div className="mb-2 text-sm"><strong>Damage Resistances:</strong> {creature.damage_resistances.join(", ")}</div>
            )}
            {creature.damage_immunities?.length > 0 && (
              <div className="mb-2 text-sm"><strong>Damage Immunities:</strong> {creature.damage_immunities.join(", ")}</div>
            )}
            {creature.condition_immunities?.length > 0 && (
              <div className="mb-2 text-sm"><strong>Condition Immunities:</strong> {creature.condition_immunities.join(", ")}</div>
            )}
            <div className="mb-2 text-sm"><strong>Senses:</strong> {creature.senses}</div>
            {creature.languages?.length > 0 && (
              <div className="mb-2 text-sm"><strong>Languages:</strong> {creature.languages.join(", ")}</div>
            )}
          </div>
          <div className="draft-right">
            {portraitUrl ? (
              <img src={portraitUrl} alt={`${creature.name} portrait`} className="portrait-img"/>
            ) : (
              <div className="portrait-placeholder">No portrait</div>
            )}
          </div>
          <div className="draft-full">
            {creature.traits?.length > 0 && (
              <div className="mb-2">
                <div className="text-sm font-semibold mb-1">Traits</div>
                <ul className="list-disc list-inside text-sm">
                  {creature.traits.map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            )}
            {creature.actions?.length > 0 && (
              <div className="mb-2">
                <div className="text-sm font-semibold mb-1">Actions</div>
                <ul className="list-disc list-inside text-sm">
                  {creature.actions.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            )}
            {creature.spells?.length > 0 && (
              <div className="mb-2 text-sm"><strong>Spells:</strong> {creature.spells.join(", ")}</div>
            )}
            <div className="mb-2 whitespace-pre-wrap text-sm" style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
              <strong>Description:</strong> {creature.description}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Bottom: actions anchored right */}
      <div className="card-actions">
        {onGeneratePortrait && (
          <LoadingButton onClick={onGeneratePortrait}>
            {portraitUrl ? 'Regenerate Portrait' : 'Generate Portrait'}
          </LoadingButton>
        )}
        <LoadingButton onClick={()=>downloadCreatureJSON(creature)}>Download JSON</LoadingButton>
        <LoadingButton onClick={()=>downloadCreatureMarkdown(creature)}>Download Markdown</LoadingButton>
        <LoadingButton onClick={onSave}>Save to Library</LoadingButton>
      </div>
    </div>
  );
}

