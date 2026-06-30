import { useState } from "react";
import { useStore } from "../store";
import { TEMPLATES } from "../templates";
import CredsPanel from "./CredsPanel";

export default function Toolbar() {
  const run = useStore((s) => s.run);
  const loadTemplate = useStore((s) => s.loadTemplate);
  const clearGraph = useStore((s) => s.clearGraph);
  const queue = useStore((s) => s.queueRemaining);
  const promptId = useStore((s) => s.promptId);
  const runError = useStore((s) => s.runError);
  const [tplOpen, setTplOpen] = useState(false);

  return (
    <>
      <div className="toolbar">
        <b className="brand">🎬 AI 短视频工作流</b>
        <button className="run" onClick={() => run()}>
          ▶ 运行
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
        {promptId && (
          <small>
            任务 {promptId.slice(0, 8)} · 队列 {queue}
          </small>
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
