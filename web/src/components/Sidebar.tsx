// no default React import needed with react-jsx runtime

function IconWand({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M15 4l5 5M2 22l9-9"/>
      <path d="M7 2v3M2 7h3M10 7h3M7 10v3"/>
    </svg>
  );
}

function IconLibrary({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M8 3H6a2 2 0 0 0-2 2v14"/>
      <rect x="8" y="3" width="8" height="18" rx="1"/>
      <path d="M20 21V5a2 2 0 0 0-2-2h-2"/>
    </svg>
  );
}


export default function Sidebar({
  expanded,
  setExpanded,
  section,
  onSelect,
  apiOk,
}: {
  expanded: boolean;
  setExpanded: (b: boolean)=>void;
  section: "char-new" | "char-lib" | "item-new" | "item-lib";
  onSelect: (s: "char-new"|"char-lib"|"item-new"|"item-lib")=>void;
  apiOk: boolean | null;
}) {
  return (
    <aside className={`sidebar ${expanded ? "" : "sidebar-collapsed"}`}>
      <div className="sidebar-header">
        <div className="app-brand" onClick={()=>setExpanded(!expanded)} title="Toggle sidebar" style={{cursor:'pointer'}}>
          <div className="brand-logo">5e</div>
          {expanded && <div className="brand-text">Forge</div>}
        </div>
      </div>

      <div className="sidebar-status">
        <span className={`status-pill ${apiOk ? "status-ok" : apiOk === false ? "status-down" : ""}`}>
          <span className="dot" />
          {expanded && (apiOk === null ? "Checking" : apiOk ? "Online" : "Offline")}
        </span>
      </div>

      <nav className="sidebar-nav">
        {expanded && <div className="nav-title">Character</div>}
        <button className={`nav-btn ${section === "char-new" ? "nav-active" : ""}`} onClick={()=>onSelect("char-new")} title="New Character">
          <IconWand />{expanded && <span>New</span>}
        </button>
        <button className={`nav-btn ${section === "char-lib" ? "nav-active" : ""}`} onClick={()=>onSelect("char-lib")} title="Character Library">
          <IconLibrary />{expanded && <span>Library</span>}
        </button>

        {expanded && <div className="nav-title" style={{marginTop:'.6rem'}}>Magic Item</div>}
        <button className={`nav-btn ${section === "item-new" ? "nav-active" : ""}`} onClick={()=>onSelect("item-new")} title="New Magic Item">
          <IconWand />{expanded && <span>New</span>}
        </button>
        <button className={`nav-btn ${section === "item-lib" ? "nav-active" : ""}`} onClick={()=>onSelect("item-lib")} title="Magic Item Library">
          <IconLibrary />{expanded && <span>Library</span>}
        </button>
      </nav>
    </aside>
  );
}
