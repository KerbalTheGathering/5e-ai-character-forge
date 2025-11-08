import type { BackstoryResult, CharacterDraft } from "../api";

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
    <div className="card-flex">
      <div className="text-sm">
        <div className="mb-2"><strong>{draft.race} {draft.cls}</strong> — Level {draft.level} · Background {draft.background} · PB {draft.proficiency_bonus} · d{draft.hit_die} · Speed {draft.speed} ft</div>
        <div className="mb-2">AC (no armor): <strong>{draft.armor_class_basic}</strong></div>
        <div className="mb-2">Languages: {draft.languages.join(", ") || "—"}</div>
        <div className="mb-2">Saving Throws: {draft.saving_throws.join(", ") || "—"}</div>
        <div className="mb-2">Proficiencies: {draft.proficiencies.map(p=>p.name).join(", ") || "—"}</div>
        <div className="mb-2">Equipment: {draft.equipment.join(", ") || "—"}</div>
        {draft.features.length > 0 && (
          <div className="mb-2">
            Features @ Level {draft.level}: {draft.features.join(", ")}
          </div>
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

      <div className="mb-2">
        <label className="block text-sm mb-1">Name</label>
        <input
          className="glass-input"
          placeholder="e.g., Kaelis Stormsinger"
          value={charName}
          onChange={(e)=>setCharName(e.target.value)}
        />
      </div>
      {portraitUrl && <div className="mt-3"><img src={portraitUrl} alt="portrait" style={{maxWidth: "240px", borderRadius: "8px", border: "1px solid rgba(192,192,192,.25)"}} /></div>}
      <div className="card-actions">
        <button className="btn mr-2" onClick={onGeneratePortrait}>Generate Portrait</button>
        <button className="btn mr-2" onClick={()=>downloadJSON(draft, backstory)}>Download JSON</button>
        <button className="btn mr-2" onClick={()=>downloadMarkdown(draft, backstory)}>Download Markdown</button>
        <button className="btn mr-2" onClick={onDownloadPDF}>Download PDF</button>
        <button className="btn" onClick={doSave}>Save to Library</button>
      </div>
    </div>
  );
}
