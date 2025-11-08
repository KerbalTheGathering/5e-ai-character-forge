import type { BackstoryResult, CharacterDraft, LengthOpt, Tone } from "../api";

export default function BackstoryPanel({
  draft,
  tone, setTone,
  lengthOpt, setLengthOpt,
  includeHooks, setIncludeHooks,
  busyBS,
  doBackstory,
  backstory,
}: {
  draft: CharacterDraft | null;
  tone: Tone; setTone: (t: Tone)=>void;
  lengthOpt: LengthOpt; setLengthOpt: (l: LengthOpt)=>void;
  includeHooks: boolean; setIncludeHooks: (b: boolean)=>void;
  busyBS: boolean;
  doBackstory: ()=>void | Promise<void>;
  backstory: BackstoryResult | null;
}){
  return (
    <div className="card-flex">
      {!draft ? <p className="text-slate-300">Generate a draft first.</p> : (
        <>
          <div className="grid gap-2" style={{gridTemplateColumns:"repeat(3,minmax(0,1fr))"}}>
            <div>
              <label className="block text-sm mb-1">Tone</label>
              <select className="glass-input" value={tone} onChange={(e)=>setTone(e.target.value as Tone)}>
                <option>heroic</option><option>grimdark</option><option>whimsical</option><option>noir</option><option>epic</option>
              </select>
            </div>
            <div>
              <label className="block text-sm mb-1">Length</label>
              <select className="glass-input" value={lengthOpt} onChange={(e)=>setLengthOpt(e.target.value as LengthOpt)}>
                <option>short</option><option>standard</option><option>long</option>
              </select>
            </div>
            <div className="flex items-end">
              <label className="text-sm">
                <input type="checkbox" className="mr-2" checked={includeHooks} onChange={(e)=>setIncludeHooks(e.target.checked)} />
                Include hooks
              </label>
            </div>
          </div>
          <div className="card-actions">
            <button disabled={busyBS} onClick={doBackstory} className={`btn ${busyBS ? "btn-disabled":""}`}>{busyBS ? "Writing…" : "Generate backstory"}</button>
          </div>
          {backstory && (
            <div className="mt-4 text-sm scroll-area">
              <div className="mb-2"><strong>Summary:</strong> {backstory.summary}</div>
              <div className="mb-2"><strong>Traits:</strong> {backstory.traits.join(", ")}</div>
              <div className="mb-2"><strong>Ideals:</strong> {backstory.ideals.join(", ")}</div>
              <div className="mb-2"><strong>Bonds:</strong> {backstory.bonds.join(", ")}</div>
              <div className="mb-2"><strong>Flaws:</strong> {backstory.flaws.join(", ")}</div>
              {backstory.hooks.length>0 && <div className="mb-2"><strong>Hooks:</strong> {backstory.hooks.join(" · ")}</div>}
              <div className="prose mt-4 whitespace-pre-wrap">{backstory.prose_markdown}</div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
