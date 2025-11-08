import { useMemo, useState } from "react";

export default function ItemLibraryTable({
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
}: {
  rows: {id:number; name:string; created_at:string}[] | null;
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
}){
  const pages = Math.max(1, Math.ceil((total||0) / pageSize));
  const slice = rows;
  return (
    <div className="card-flex">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold mb-3">Magic Item Library</h2>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <input className="glass-input" placeholder="Search" value={search} onChange={(e)=>onSearchChange(e.target.value)} style={{width:180}} />
          <select className="glass-input" value={sort} onChange={(e)=>onSortChange(e.target.value)} style={{width:160}}>
            <option value="created_desc">Newest</option>
            <option value="created_asc">Oldest</option>
            <option value="name_asc">Name A→Z</option>
            <option value="name_desc">Name Z→A</option>
          </select>
          <button className={`btn ${busy ? 'btn-disabled':''}`} onClick={onRefresh}>{busy? 'Loading…':'Refresh'}</button>
        </div>
      </div>
      {!slice || slice.length===0 ? (
        <p className="text-slate-300">No items saved yet.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Name</th><th>Created</th><th style={{width:'1%'}}>Actions</th></tr>
            </thead>
            <tbody>
              {slice.map(r => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td className="text-slate-400">{r.created_at}</td>
                  <td>
                    <button className="btn mr-2" onClick={()=>onSelect(r.id)}>Open</button>
                    <button className="btn" onClick={()=>onDelete(r.id)}>Delete</button>
                  </td>
                </tr>
              ))}
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
