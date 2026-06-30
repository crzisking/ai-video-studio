import { Handle, Position, useUpdateNodeInternals, type NodeProps } from "reactflow";
import { useEffect, useMemo } from "react";
import type { GraphNodeData } from "../types";
import { allInputs, categoryAccent, declType, isWidgetType, socketColor } from "../graph";
import { useStore } from "../store";
import { uploadFile } from "../api";

const STATUS: Record<string, { color: string; label: string }> = {
  idle: { color: "#5a5a5a", label: "待运行" },
  queued: { color: "#b58900", label: "排队中" },
  executing: { color: "#268bd2", label: "运行中" },
  done: { color: "#2aa198", label: "完成" },
  cached: { color: "#6c71c4", label: "缓存命中" },
  error: { color: "#dc322f", label: "出错" },
};

export default function DynamicNode({ id, data, selected }: NodeProps<GraphNodeData>) {
  const def = data.def;
  const edges = useStore((s) => s.edges);
  const updateNodeValue = useStore((s) => s.updateNodeValue);
  const togglePin = useStore((s) => s.togglePin);
  const rerunNode = useStore((s) => s.rerunNode);
  const deleteNode = useStore((s) => s.deleteNode);
  const updateNodeInternals = useUpdateNodeInternals();

  const connected = useMemo(() => {
    const set = new Set<string>();
    for (const e of edges) if (e.target === id) set.add((e.targetHandle || "").replace(/^in:/, ""));
    return set;
  }, [edges, id]);

  // 连接状态/预览/报错会改变节点高度→端口坐标变化，必须通知 reactflow 重测，
  // 否则连线画错位置且后续连接命中失效（连不上）。
  const layoutKey =
    [...connected].sort().join(",") + "|" + (data.preview?.length || 0) + "|" + (data.error ? 1 : 0);
  useEffect(() => {
    updateNodeInternals(id);
  }, [layoutKey, id, updateNodeInternals]);

  const inputs = allInputs(def);
  const requiredNames = new Set(Object.keys(def.input.required || {}));
  const st = STATUS[data.status || "idle"] || STATUS.idle;
  const accent = categoryAccent(def.category);

  return (
    <div
      className={`vnode ${data.pinned ? "pinned" : ""} ${selected ? "selected" : ""} st-${data.status || "idle"}`}
      style={{ ["--accent" as any]: accent }}
    >
      <div className="vnode-head">
        <span className="dot" style={{ background: st.color }} title={st.label} />
        <span className="title">{def.name}</span>
        {def.is_cloud_task && <span className="badge">云任务</span>}
        <span className="grow" />
        <button title="锁定：重跑时不动它" className={`mini ${data.pinned ? "on" : ""}`} onClick={() => togglePin(id)}>
          📌
        </button>
        <button title="只重新生成此节点" className="mini" onClick={() => rerunNode(id)}>
          ↻
        </button>
        <button title="删除节点" className="mini danger" onClick={() => deleteNode(id)}>
          ✕
        </button>
      </div>

      <div className="vnode-body">
        {inputs.map(([name, spec]) => {
          const t = spec[0];
          const opts = spec[1] || {};
          const isConn = connected.has(name);
          const widget = isWidgetType(t) && !isConn;
          const isUpload = def.name === "LoadReference" && name === "paths";
          // 必填、且只能靠连线的端口（非 widget 类型），未连时高亮提示
          const needsLink = requiredNames.has(name) && !isWidgetType(t) && !isConn;
          return (
            <div className={`port in ${widget ? "has-widget" : ""} ${needsLink ? "need-link" : ""}`} key={"in-" + name}>
              <Handle id={"in:" + name} type="target" position={Position.Left}
                      className="vh" style={{ background: socketColor(declType(t)) }} />
              <div className="port-label">
                {name}
                {needsLink && <span className="need-tag">需连接</span>}
                {isUpload && <UploadButton onUploaded={(names) =>
                  updateNodeValue(id, "paths", [(data.values.paths || "").trim(), ...names].filter(Boolean).join("\n"))} />}
              </div>
              {widget && (
                <Widget t={t} opts={opts} value={data.values[name]}
                        onChange={(v) => updateNodeValue(id, name, v)} />
              )}
            </div>
          );
        })}

        {def.output.map((ot, i) => (
          <div className="port out" key={"out-" + i}>
            <span className="port-label">{def.output_name[i] || ot}</span>
            <Handle id={"out:" + i} type="source" position={Position.Right}
                    className="vh" style={{ background: socketColor(ot) }} />
          </div>
        ))}

        {(data.preview || []).map((p, i) =>
          p.url && p.type === "image" ? (
            <img key={i} className="preview" src={p.url} />
          ) : p.url && (p.type === "video" || p.type === "final") ? (
            <video key={i} className="preview" src={p.url} controls />
          ) : p.url && p.type === "audio" ? (
            <audio key={i} className="preview-audio" src={p.url} controls />
          ) : null
        )}
        {data.error && <div className="err">{data.error}</div>}
      </div>
    </div>
  );
}

function Widget({ t, opts, value, onChange }:
  { t: string | string[]; opts: any; value: any; onChange: (v: any) => void }) {
  if (Array.isArray(t)) {
    return (
      <select className="w" value={value} onChange={(e) => onChange(e.target.value)}>
        {t.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  }
  if (t === "INT" || t === "FLOAT") {
    return (
      <input className="w" type="number" value={value ?? 0} min={opts.min} max={opts.max}
             step={t === "INT" ? 1 : opts.step || 0.1} onChange={(e) => onChange(e.target.value)} />
    );
  }
  if (t === "BOOLEAN") {
    return <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} />;
  }
  if (opts.multiline) {
    return <textarea className="w" value={value ?? ""} rows={3}
                     placeholder={opts.default ? "" : "输入…"}
                     onChange={(e) => onChange(e.target.value)} />;
  }
  return <input className="w" type="text" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />;
}

function UploadButton({ onUploaded }: { onUploaded: (names: string[]) => void }) {
  return (
    <label className="upload">
      ＋上传
      <input type="file" style={{ display: "none" }} onChange={async (e) => {
        const f = e.target.files?.[0];
        if (!f) return;
        const r = await uploadFile(f);
        onUploaded(r.names);
        e.target.value = "";
      }} />
    </label>
  );
}
