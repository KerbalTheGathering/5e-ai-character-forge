export type TabItem = {
  key: string;
  label: string;
};

export function Tabs({ tabs, active, onChange }: { tabs: TabItem[]; active: string; onChange: (key: string)=>void }) {
  return (
    <div className="tabs">
      {tabs.map(t => (
        <button
          key={t.key}
          className={`tab ${active === t.key ? "tab-active" : ""}`}
          onClick={()=>onChange(t.key)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
