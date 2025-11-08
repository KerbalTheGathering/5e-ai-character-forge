import type { BackstoryResult, CharacterDraft } from "../api";
import LoadingButton from "./LoadingButton";

export default function DraftPanel({
  draft,
  backstory,
  charName,
  setCharName,
  downloadJSON,
  downloadMarkdown,
  doSave,
  portraitUrl,
  onGeneratePortrait,
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
  onGeneratePortrait: ()=>void | Promise<void>;
  onDownloadPDF: ()=>void | Promise<void>;
}){
  return (
    <div className="card-flex" style={{minHeight: 280}}>
      {/* Top: Name (half width) */}
      <div className="mb-2" style={{ width: '50%' }}>
        <label className="block text-sm mb-1">Name</label>
        <input
          className="glass-input"
          placeholder="e.g., Kaelis Stormsinger"
          value={charName}
          onChange={(e)=>setCharName(e.target.value)}
        />
      </div>

      {/* Middle: details left, portrait right */}
      <div className="draft-grid flex-scroll">
        <div className="draft-left text-sm">
          <div className="mb-2"><strong>{draft.race} {draft.cls}</strong> — Level {draft.level} · Background {draft.background} · PB {draft.proficiency_bonus} · d{draft.hit_die} · Speed {draft.speed} ft</div>
          <div className="mb-2">AC (no armor): <strong>{draft.armor_class_basic}</strong></div>
          <div className="mb-2">Languages: {draft.languages.join(", ") || "—"}</div>
          <div className="mb-2">Saving Throws: {draft.saving_throws.join(", ") || "—"}</div>
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
        </div>
        <div className="draft-right">
          {portraitUrl ? (
            <img src={portraitUrl} alt="portrait" className="portrait-img"/>
          ) : (
            <div className="portrait-placeholder">No portrait</div>
          )}
        </div>
      </div>

      {/* Bottom: actions anchored right */}
      <div className="card-actions">
        <LoadingButton onClick={onGeneratePortrait}>Generate Portrait</LoadingButton>
        <LoadingButton onClick={()=>downloadJSON(draft, backstory)}>Download JSON</LoadingButton>
        <LoadingButton onClick={()=>downloadMarkdown(draft, backstory)}>Download Markdown</LoadingButton>
        <LoadingButton onClick={onDownloadPDF}>Download PDF</LoadingButton>
        <LoadingButton onClick={doSave}>Save to Library</LoadingButton>
      </div>
    </div>
  );
}
