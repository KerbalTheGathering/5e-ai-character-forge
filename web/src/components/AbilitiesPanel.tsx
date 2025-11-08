import type { Ability, AbilitySet } from "../api";
import LoadingButton from "./LoadingButton";

const ABILS: Ability[] = ["STR","DEX","CON","INT","WIS","CHA"];

export default function AbilitiesPanel({
  abilities, assignment, setAssignment, canGenerate, busy, doGenerate,
}: {
  abilities: AbilitySet | null;
  assignment: Ability[];
  setAssignment: (a: Ability[])=>void;
  canGenerate: boolean;
  busy: boolean;
  doGenerate: ()=>void;
}){
  function scoreFor(i: number){ return abilities ? abilities.scores[i] : 10; }
  return (
    <div className="card-flex">
      {!abilities ? <p className="text-slate-300">No rolls yet.</p> : (
        <>
          <div className="text-sm text-slate-300 mb-2">Sorted (high→low): {abilities.scores.join(", ")}</div>
          <div className="grid gap-2" style={{gridTemplateColumns:"repeat(2,minmax(0,1fr))", columnGap: "2rem"}}>
            {ABILS.map((ab, i)=>(
              <div key={ab} className="ability-row">
                <select
                  className="glass-input"
                  style={{ width: 'auto', minWidth: '110px' }}
                  value={assignment[i]}
                  onChange={(e)=>{
                    const copy = [...assignment] as Ability[]; copy[i] = e.target.value as Ability; setAssignment(copy);
                  }}
                >
                  {ABILS.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
                <div className="text-xs text-slate-400">gets score <strong>{scoreFor(i)}</strong></div>
              </div>
            ))}
          </div>
          <div className="card-actions">
            <LoadingButton loading={busy} disabled={!canGenerate} onClick={doGenerate}>Generate draft</LoadingButton>
          </div>
        </>
      )}
    </div>
  );
}
