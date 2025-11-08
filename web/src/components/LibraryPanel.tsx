export default function LibraryPanel({
  lib,
  busyLib,
  doListLib,
  doLoad,
  doDelete,
}: {
  lib: {id:number; name:string; created_at:string}[] | null;
  busyLib: boolean;
  doListLib: ()=>void | Promise<void>;
  doLoad: (id: number)=>void | Promise<void>;
  doDelete: (id: number)=>void | Promise<void>;
}){
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold mb-3">Library</h2>
        <button className={`btn ${busyLib ? "btn-disabled":""}`} onClick={doListLib}>{busyLib ? "Loading…" : "Refresh"}</button>
      </div>
      {!lib || lib.length === 0 ? (
        <p className="text-slate-300">No saved characters yet. Save one, then click Refresh.</p>
      ) : (
        <ul className="text-sm">
          {lib.map(item => (
            <li key={item.id} className="border-t border-white/10 py-2 flex items-center justify-between">
              <div>
                <div className="font-semibold">{item.name}</div>
                <div className="text-slate-400">{item.created_at} · id {item.id}</div>
              </div>
              <div>
                <button className="btn mr-2" onClick={()=>doLoad(item.id)}>Open</button>
                <button className="btn" onClick={()=>doDelete(item.id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

