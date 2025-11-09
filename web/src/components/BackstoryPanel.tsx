import type { BackstoryResult, CharacterDraft, LengthOpt, Tone } from "../api";
import GlassCard from "./GlassCard";
import LoadingButton from "./LoadingButton";

export default function BackstoryPanel({
  draft,
  tone, setTone,
  lengthOpt, setLengthOpt,
  includeHooks, setIncludeHooks,
  customInspiration, setCustomInspiration,
  busyBS,
  doBackstory,
  backstory,
}: {
  draft: CharacterDraft | null;
  tone: Tone; setTone: (t: Tone)=>void;
  lengthOpt: LengthOpt; setLengthOpt: (l: LengthOpt)=>void;
  includeHooks: boolean; setIncludeHooks: (b: boolean)=>void;
  customInspiration: string; setCustomInspiration: (s: string)=>void;
  busyBS: boolean;
  doBackstory: ()=>void | Promise<void>;
  backstory: BackstoryResult | null;
}){
  return (
    // Fill parent card height so actions sit at bottom to align with Draft sheet
    <div className="card-flex" style={{ height: '100%' }}>
      {!draft ? (
        <GlassCard className="fill-card card-red-gradient">
          <p className="text-slate-300">Generate a draft first.</p>
        </GlassCard>
      ) : (
        <GlassCard className="fill-card">
          <div className="card-flex" style={{ height: '100%' }}>
            <h2 className="text-xl font-semibold mb-3">Backstory</h2>
            <div className="grid gap-2" style={{gridTemplateColumns:"repeat(3,minmax(0,1fr))"}}>
              <div>
                <label className="block text-sm mb-1">Tone</label>
                <select className="glass-input" value={tone} onChange={(e)=>setTone(e.target.value as Tone)}>
                  <option>custom</option><option>heroic</option><option>grimdark</option><option>whimsical</option><option>noir</option><option>epic</option>
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
            {tone === "custom" && (
              <div className="mt-2">
                <label className="block text-sm mb-1">Custom Inspiration</label>
                <textarea
                  className="glass-input w-full"
                  rows={4}
                  placeholder="Enter your custom inspiration for the backstory..."
                  value={customInspiration}
                  onChange={(e)=>setCustomInspiration(e.target.value)}
                />
              </div>
            )}
            {backstory && (
              <GlassCard>
                <div className="mt-4 text-sm flex-scroll" style={{ paddingRight: '1.25rem', paddingLeft: '.5rem', flex: '1 1 auto', minHeight: 0 }}>
                  <div className="mb-2"><strong>Summary:</strong> {backstory.summary}</div>
                  <div className="mb-2"><strong>Traits:</strong> {backstory.traits.join(", ")}</div>
                  <div className="mb-2"><strong>Ideals:</strong> {backstory.ideals.join(", ")}</div>
                  <div className="mb-2"><strong>Bonds:</strong> {backstory.bonds.join(", ")}</div>
                  <div className="mb-2"><strong>Flaws:</strong> {backstory.flaws.join(", ")}</div>
                  {backstory.hooks.length>0 && <div className="mb-2"><strong>Hooks:</strong> {backstory.hooks.join(" · ")}</div>}
                  <div className="prose mt-4 whitespace-pre-wrap">{backstory.prose_markdown}</div>
                </div>
              </GlassCard>
            )}
            <div className="card-actions">
              <LoadingButton loading={busyBS} onClick={doBackstory}>Generate backstory</LoadingButton>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
