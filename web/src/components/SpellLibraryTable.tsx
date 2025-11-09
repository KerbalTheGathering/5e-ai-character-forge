import { useMemo } from "react";
import LoadingButton from "./LoadingButton";

export default function SpellLibraryTable({
  rows,
  total,
  page,
  pageSize,
  search,
  sort,
  busy,
  onRefresh,
  onSelect,
  onDelete,
  onPageChange,
  onSearchChange,
  onSortChange,
  twoPanelMode = false,
}: {
  rows: {id:number; name:string; created_at:string; level?:number; school?:string}[] | null;
  total: number;
  page: number;
  pageSize: number;
  search: string;
  sort: string;
  busy: boolean;
  onRefresh: ()=>void | Promise<void>;
  onSelect: (id:number)=>void | Promise<void>;
  onDelete: (id:number)=>void | Promise<void>;
  onPageChange: (p:number)=>void;
  onSearchChange: (q:string)=>void;
  onSortChange: (s:string)=>void;
  twoPanelMode?: boolean;
}){
  const pages = Math.max(1, Math.ceil((total||0) / pageSize));
  const slice = rows;
  return (
    <div className="card-flex">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold mb-3">Spells Library</h2>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <input className="glass-input" placeholder="Search" value={search} onChange={(e)=>onSearchChange(e.target.value)} style={{width:180}} />
          <select className="glass-input" value={sort} onChange={(e)=>onSortChange(e.target.value)} style={{width:160}}>
            <option value="created_desc">Newest</option>
            <option value="created_asc">Oldest</option>
            <option value="name_asc">Name A→Z</option>
            <option value="name_desc">Name Z→A</option>
          </select>
          <LoadingButton loading={busy} onClick={onRefresh}>Refresh</LoadingButton>
        </div>
      </div>
      {!slice || slice.length===0 ? (
        <p className="text-slate-300">No spells saved yet.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              {twoPanelMode ? (
                <tr><th>Name</th><th className="actions-col">Actions</th></tr>
              ) : (
                <tr><th>Name</th><th>Created</th><th className="actions-col">Actions</th></tr>
              )}
            </thead>
            <tbody>
              {slice.map(r => {
                const level = r.level !== undefined ? r.level : null;
                const school = r.school || "";
                const levelLabel = level === 0 ? "Cantrip" : `Level ${level}`;
                const nameDisplay = level !== null && school 
                  ? `${r.name}: ${levelLabel} ${school}`
                  : r.name;
                return (
                  <tr key={r.id}>
                    <td>{nameDisplay}</td>
                    {!twoPanelMode && <td className="text-slate-400">{r.created_at}</td>}
                    <td className="actions-cell">
                      <LoadingButton onClick={()=>onSelect(r.id)}>Open</LoadingButton>
                      <LoadingButton onClick={()=>onDelete(r.id)}>Delete</LoadingButton>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="card-actions">
        <span className="text-slate-400" style={{marginRight:'auto'}}>Page {page} / {pages}</span>
        <button className="btn mr-2" onClick={()=>onPageChange(Math.max(1,page-1))} disabled={page<=1}>Prev</button>
        <button className="btn" onClick={()=>onPageChange(Math.min(pages,page+1))} disabled={page>=pages}>Next</button>
      </div>
    </div>
  );
}
