import clsx from "clsx";

interface Tab {
  id: string;
  label: string;
}

interface Props {
  tabs: Tab[];
  activeTab: string;
  onChange: (id: string) => void;
}

export function Tabs({ tabs, activeTab, onChange }: Props) {
  return (
    <div className="border-b border-slate-200">
      <nav className="-mb-px flex gap-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={clsx(
              "whitespace-nowrap border-b-2 py-3 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-primary-600 text-primary-600"
                : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700",
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
