import type { CharacterDraft, BackstoryResult } from "../api";
import GlassCard from "./GlassCard";
import LoadingButton from "./LoadingButton";

export default function PortraitPanel({
  draft,
  portraitUrl,
  portraitPrompt,
  setPortraitPrompt,
  useBackstoryPrompt,
  setUseBackstoryPrompt,
  backstory,
  busyPortrait,
  onGeneratePortrait,
  onAddToDraft,
}: {
  draft: CharacterDraft | null;
  portraitUrl: string | null;
  portraitPrompt: string;
  setPortraitPrompt: (p: string) => void;
  useBackstoryPrompt: boolean;
  setUseBackstoryPrompt: (b: boolean) => void;
  backstory: BackstoryResult | null;
  busyPortrait: boolean;
  onGeneratePortrait: () => void | Promise<void>;
  onAddToDraft: () => void | Promise<void>;
}) {
  return (
    <div className="card-flex" style={{ height: '100%' }}>
      {!draft ? (
        <GlassCard className="fill-card card-red-gradient">
          <p className="text-slate-300">Generate a draft first.</p>
        </GlassCard>
      ) : (
        <GlassCard className="fill-card">
          <div className="card-flex" style={{ height: '100%' }}>
            <h2 className="text-xl font-semibold mb-3">Portrait</h2>
            
            {/* Top section: Checkbox and text area (takes ~1/3) */}
            <div className="mb-4" style={{ flex: '0 0 auto' }}>
              <label className="text-sm mb-2 block">
                <input
                  type="checkbox"
                  className="mr-2"
                  checked={useBackstoryPrompt}
                  onChange={(e) => setUseBackstoryPrompt(e.target.checked)}
                />
                Use backstory as prompt
              </label>
              {!useBackstoryPrompt && (
                <div className="mt-2">
                  <label className="block text-sm mb-1">Custom Portrait Prompt</label>
                  <textarea
                    className="glass-input w-full"
                    rows={4}
                    placeholder="Enter your custom prompt for the portrait..."
                    value={portraitPrompt}
                    onChange={(e) => setPortraitPrompt(e.target.value)}
                  />
                </div>
              )}
            </div>

            {/* Bottom 2/3rds: Preview area (square) */}
            <div className="flex items-center justify-center mb-4" style={{ minHeight: 0, flex: '2 1 auto', aspectRatio: '1' }}>
              {portraitUrl ? (
                <img
                  src={portraitUrl}
                  alt="Portrait preview"
                  className="portrait-img"
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', aspectRatio: '1' }}
                />
              ) : (
                <div className="portrait-placeholder" style={{ width: '100%', aspectRatio: '1', maxWidth: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div className="text-slate-400">Preview not found</div>
                </div>
              )}
            </div>

            {/* Bottom: Actions */}
            <div className="card-actions">
              <LoadingButton loading={busyPortrait} onClick={onAddToDraft}>
                Add to Draft
              </LoadingButton>
              <LoadingButton loading={busyPortrait} onClick={onGeneratePortrait}>
                Generate Portrait
              </LoadingButton>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}

