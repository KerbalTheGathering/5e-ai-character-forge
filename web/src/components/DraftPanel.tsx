import type { BackstoryResult, CharacterDraft } from "../api";
import LoadingButton from "./LoadingButton";
import GlassCard from "./GlassCard";

export default function DraftPanel({
  draft,
  backstory,
  charName,
  setCharName,
  downloadJSON,
  downloadMarkdown,
  doSave,
  portraitUrl,
  onDownloadPDF,
}: {
  draft: CharacterDraft;
  backstory: BackstoryResult | null;
  charName: string;
  setCharName: (v: string)=>void;
  downloadJSON: (d: CharacterDraft, b?: BackstoryResult | null)=>void | Promise<void>;
  downloadMarkdown: (d: CharacterDraft, b?: BackstoryResult | null)=>void | Promise<void>;
  doSave: ()=>void | Promise<void>;
  portraitUrl: string | null;
  onDownloadPDF: ()=>void | Promise<void>;
}){
  return (
    <div className="card-flex" style={{minHeight: 280}}>
      {/* Middle: details left, portrait right (wrapped in frosted glass card) */}
      <GlassCard className="flex-scroll">
        {/* Top: Name (half width) */}
      <div className="mb-2" style={{ width: '50%' }}>
        <div className="text-slate-400 font-semibold">{charName || draft.name || "—"}</div>
      </div>
        <div className="draft-grid">
          <div className="draft-left text-sm">
            <div className="mb-2"><strong>{draft.race} {draft.cls}</strong> — Level {draft.level} · Background {draft.background}</div> 
            <div className="mb-2">PB {draft.proficiency_bonus} · d{draft.hit_die} · Speed {draft.speed} ft</div>
            <div className="mb-2">AC (no armor): <strong>{draft.armor_class_basic}</strong></div>
            {/* Abilities */}
            <div className="mb-2">
              <div className="text-slate-300 text-sm mb-1">Abilities</div>
              <div className="grid gap-2" style={{gridTemplateColumns: "repeat(3, minmax(0, 1fr))"}}>
                {([
                  ['STR', draft.abilities.STR, draft.abilities.STR_mod],
                  ['DEX', draft.abilities.DEX, draft.abilities.DEX_mod],
                  ['CON', draft.abilities.CON, draft.abilities.CON_mod],
                  ['INT', draft.abilities.INT, draft.abilities.INT_mod],
                  ['WIS', draft.abilities.WIS, draft.abilities.WIS_mod],
                  ['CHA', draft.abilities.CHA, draft.abilities.CHA_mod],
                ] as [string, number, number][]).map(([abbr, score, mod]) => (
                  <div key={abbr} className="bg-black/40 rounded border border-white/10 p-2 text-center">
                    <div className="text-xs text-slate-400">{abbr}</div>
                    <div className="text-lg font-semibold">{score}</div>
                    <div className="text-xs text-slate-300">{mod >= 0 ? `(+${mod})` : `(${mod})`}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="mb-2">Languages: {draft.languages.join(", ") || "—"}</div>
            <div className="mb-2">Saving Throws: {draft.saving_throws.join(", ") || "—"}</div>
            
          </div>
          <div className="draft-right">
            {portraitUrl ? (
              <img src={portraitUrl} alt="portrait" className="portrait-img"/>
            ) : (
              <div className="portrait-placeholder">No portrait</div>
            )}
          </div>
          <div className="draft-full">
            <div className="mb-2">Proficiencies: {draft.proficiencies.map(p=>p.name).join(", ") || "—"}</div>
            <div className="mb-2">Equipment: {draft.equipment.join(", ") || "—"}</div>
            {draft.features.length > 0 && (
              <div className="mb-2">Features @ Level {draft.level}: {draft.features.join(", ")} </div>
            )}
            {draft.spell_slots && Object.keys(draft.spell_slots).length > 0 && (
              <div className="mb-2">
                Spell Slots:{" "}
                {Object.entries(draft.spell_slots)
                  .sort(([a], [b]) => Number(a) - Number(b))
                  .map(([lvl, count]) => `${lvl}:${count}`)
                  .join(" · ")}
              </div>
            )}
            <div className="mb-2" style={{ wordBreak: 'break-word', overflowWrap: 'break-word' }}>
              <strong>Backstory:</strong> {backstory ? backstory.summary : "—"}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Bottom: actions anchored right */}
      <div className="card-actions">
        <LoadingButton onClick={()=>downloadJSON(draft, backstory)}>Download JSON</LoadingButton>
        <LoadingButton onClick={()=>downloadMarkdown(draft, backstory)}>Download Markdown</LoadingButton>
        <LoadingButton onClick={onDownloadPDF}>Download PDF</LoadingButton>
        <LoadingButton onClick={doSave}>Save to Library</LoadingButton>
      </div>
    </div>
  );
}
