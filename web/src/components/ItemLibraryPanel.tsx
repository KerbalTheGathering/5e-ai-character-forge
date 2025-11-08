export default function ItemLibraryPanel({
  lib,
  busy,
  onRefresh,
  onOpen,
  onDelete,
}: {
  lib: {id:number; name:string; created_at:string}[] | null;
  busy: boolean;
  onRefresh: ()=>void | Promise<void>;
  onOpen: (id:number)=>void | Promise<void>;
  onDelete: (id:number)=>void | Promise<void>;
}){
  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold mb-3">Magic Item Library</h2>
        <button className={`btn ${busy ? 'btn-disabled':''}`} onClick={onRefresh}>{busy? 'Loading…':'Refresh'}</button>
      </div>
      {!lib || lib.length===0 ? <p className="text-slate-300">No items saved yet.</p> : (
        <ul className="text-sm">
          {lib.map(it => (
            <li key={it.id} className="border-t border-white/10 py-2 flex items-center justify-between">
              <div>
                <div className="font-semibold">{it.name}</div>
                <div className="text-slate-400">{it.created_at} · id {it.id}</div>
              </div>
              <div>
                <button className="btn mr-2" onClick={()=>onOpen(it.id)}>Open</button>
                <button className="btn" onClick={()=>onDelete(it.id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

