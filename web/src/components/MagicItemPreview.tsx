import { downloadItemJSON, downloadItemMarkdown, downloadItemPDF, type MagicItem } from "../api";

export default function MagicItemPreview({ item, onSave }: { item: MagicItem | null; onSave: ()=>void | Promise<void> }){
  if (!item) return <p className="text-slate-300">No item generated yet.</p>;
  return (
    <div className="text-sm card-flex">
      <div>
        <div className="mb-2"><strong>{item.name}</strong> — {item.item_type} · {item.rarity} · {item.requires_attunement ? 'Requires Attunement' : 'No Attunement'}</div>
        <div className="mb-2 whitespace-pre-wrap">{item.description}</div>
        {item.properties?.length>0 && (
          <div className="mb-2">Properties: {item.properties.join(" · ")}</div>
        )}
      </div>
      <div className="card-actions">
        <button className="btn mr-2" onClick={()=>downloadItemJSON(item)}>Download JSON</button>
        <button className="btn mr-2" onClick={()=>downloadItemMarkdown(item)}>Download Markdown</button>
        <button className="btn mr-2" onClick={()=>downloadItemPDF(item)}>Download PDF</button>
        <button className="btn" onClick={onSave}>Save to Library</button>
      </div>
    </div>
  );
}
