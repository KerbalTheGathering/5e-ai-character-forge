import { downloadItemJSON, downloadItemMarkdown, downloadItemPDF, type MagicItem } from "../api";
import LoadingButton from "./LoadingButton";

export default function MagicItemPreview({ item, onSave }: { item: MagicItem | null; onSave: ()=>void | Promise<void> }){
  if (!item) return <p className="text-slate-300">No item generated yet.</p>;
  return (
    <div className="text-sm card-flex">
      <div>
        <div className="mb-2">
          <div className="text-xl font-semibold mb-1">{item.name}</div>
          <div className="text-sm text-slate-300">{item.item_type} · {item.rarity} · {item.requires_attunement ? 'Requires Attunement' : 'No Attunement'}</div>
        </div>
        <div className="mb-2 whitespace-pre-wrap">{item.description}</div>
        {item.properties?.length>0 && (
          <div className="mb-2">Properties: {item.properties.join(" · ")}</div>
        )}
      </div>
      <div className="card-actions">
        <LoadingButton className="mr-2" onClick={()=>downloadItemJSON(item)}>Download JSON</LoadingButton>
        <LoadingButton className="mr-2" onClick={()=>downloadItemMarkdown(item)}>Download Markdown</LoadingButton>
        <LoadingButton className="mr-2" onClick={()=>downloadItemPDF(item)}>Download PDF</LoadingButton>
        <LoadingButton onClick={onSave}>Save to Library</LoadingButton>
      </div>
    </div>
  );
}
