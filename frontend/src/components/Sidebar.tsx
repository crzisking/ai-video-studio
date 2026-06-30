import { useMemo } from "react";
import { useStore } from "../store";
import { categoryAccent } from "../graph";

// 节点面板：按 category 分组，点一下在画布中央加一个节点。
export default function Sidebar() {
  const objectInfo = useStore((s) => s.objectInfo);
  const addNodeOfType = useStore((s) => s.addNodeOfType);

  const grouped = useMemo(() => {
    const g: Record<string, string[]> = {};
    for (const [name, def] of Object.entries(objectInfo)) {
      (g[def.category] = g[def.category] || []).push(name);
    }
    return g;
  }, [objectInfo]);

  return (
    <div className="sidebar">
      <h3>节点</h3>
      {Object.entries(grouped).map(([cat, names]) => (
        <div key={cat} className="cat" style={{ ["--cat" as any]: categoryAccent(cat) }}>
          <div className="cat-title">{cat}</div>
          {names.map((n) => (
            <button
              key={n}
              className="node-btn"
              onClick={() => addNodeOfType(n)}
            >
              {n}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
