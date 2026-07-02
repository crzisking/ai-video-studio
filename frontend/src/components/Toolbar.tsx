import { useState } from "react";
import { useStore } from "../store";
import { TEMPLATES } from "../templates";
import CredsPanel from "./CredsPanel";

export default function Toolbar() {
  const run = useStore((s) => s.run);
  const loadTemplate = useStore((s) => s.loadTemplate);
  const clearGraph = useStore((s) => s.clearGraph);
  const nodes = useStore((s) => s.nodes);
  const promptId = useStore((s) => s.promptId);
  const runError = useStore((s) => s.runError);
  const [tplOpen, setTplOpen] = useState(false);

  // 全局运行状态：从各节点状态汇总
  const total = nodes.length;
  const done = nodes.filter((n) => n.data.status === "done" || n.data.status === "cached").length;
  const executing = nodes.find((n) => n.data.status === "executing");
  const running = nodes.some((n) => n.data.status === "queued" || n.data.status === "executing");
  const allDone = total > 0 && !running && done === total && !!promptId;

  return (
    <>
      <div className="toolbar">
        <b className="brand">🎬 AI 短视频工作流</b>
        <button className={`run ${running ? "busy" : ""}`} onClick={() => run()} disabled={running}>
          {running ? "⏳ 运行中…" : "▶ 运行"}
        </button>

        <div className="dropdown">
          <button className="ghost" onClick={() => setTplOpen((v) => !v)}>
            📋 模板 ▾
          </button>
          {tplOpen && (
            <div className="dropdown-body" onMouseLeave={() => setTplOpen(false)}>
              {TEMPLATES.map((t) => (
                <button
                  key={t.key}
                  className="tpl-item"
                  onClick={() => {
                    loadTemplate(t.key);
                    setTplOpen(false);
                  }}
                >
                  <b>{t.name}</b>
                  <small>{t.desc}</small>
                </button>
              ))}
            </div>
          )}
        </div>

        <button className="ghost" onClick={() => clearGraph()}>
          🗑 清空
        </button>
        <CredsPanel />
        <span className="grow" />

        {/* 运行状态指示 */}
        {running && (
          <div className="status-pill busy">
            <span className="spinner" />
            运行中 · 已完成 {done}/{total}
            {executing && <b className="cur">正在跑：{executing.data.def.name}</b>}
          </div>
        )}
        {allDone && <div className="status-pill ok">✓ 全部完成（{total} 个节点）</div>}
        {promptId && (
          <small className="taskid">任务 {promptId.slice(0, 8)}</small>
        )}
      </div>
      {runError && (
        <div className="toast">
          <span>⚠</span>
          <div style={{ flex: 1 }}>{runError}</div>
          <button className="x" onClick={() => useStore.setState({ runError: null })}>
            ✕
          </button>
        </div>
      )}
    </>
  );
}
