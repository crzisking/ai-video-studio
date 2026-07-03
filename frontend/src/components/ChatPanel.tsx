import { useState } from "react";
import { useStore, type Asset } from "../store";
import { uploadFile } from "../api";

// AI 对话面板：描述需求（可附参考图）→ AI 出分镜方案 → 一键生成到画布。
export default function ChatPanel() {
  const chat = useStore((s) => s.chat);
  const busy = useStore((s) => s.agentBusy);
  const sendAgentMessage = useStore((s) => s.sendAgentMessage);
  const applyPlan = useStore((s) => s.applyPlan);
  const [text, setText] = useState("");
  const [open, setOpen] = useState(true);
  const [max, setMax] = useState(false);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [uploading, setUploading] = useState(false);

  const send = () => {
    const m = text.trim();
    if ((!m && assets.length === 0) || busy) return;
    setText("");
    const a = assets;
    setAssets([]);
    sendAgentMessage(m || "根据这些参考图编排一条短视频", a);
  };

  const addFiles = async (files: File[]) => {
    const imgs = files.filter((f) => f.type.startsWith("image/"));
    if (imgs.length === 0) return;
    setUploading(true);
    try {
      for (const f of imgs) {
        const r = await uploadFile(f);
        r.names.forEach((name, i) => setAssets((prev) => [...prev, { name, url: r.urls?.[i] }]));
      }
    } finally {
      setUploading(false);
    }
  };
  const onPick = (files: FileList | null) => files && addFiles(Array.from(files));
  const onPaste = (e: React.ClipboardEvent) => {
    const files = Array.from(e.clipboardData.files || []);
    if (files.some((f) => f.type.startsWith("image/"))) {
      e.preventDefault();
      addFiles(files);
    }
  };
  const onDrop = (e: React.DragEvent) => {
    const files = Array.from(e.dataTransfer.files || []);
    if (files.some((f) => f.type.startsWith("image/"))) {
      e.preventDefault();
      addFiles(files);
    }
  };

  if (!open) {
    return (
      <button className="chat-fab" onClick={() => setOpen(true)} title="AI 助手">
        🤖 AI 助手
      </button>
    );
  }

  return (
    <div className={`chat ${max ? "max" : ""}`}>
      <div className="chat-head">
        <b>🤖 AI 导演</b>
        <span className="grow" />
        <button className="mini" onClick={() => setMax((v) => !v)} title={max ? "还原" : "放大"}>
          {max ? "🗗" : "🗖"}
        </button>
        <button className="mini" onClick={() => setOpen(false)} title="收起">
          ✕
        </button>
      </div>

      <div className="chat-body" onDrop={onDrop} onDragOver={(e) => e.preventDefault()}>
        {chat.length === 0 && (
          <div className="chat-empty">
            描述你想要的短视频，我来出分镜方案并连好节点图。可附参考图（产品/角色），我会围绕它编排并保持主体一致。
            <div className="chat-egs">
              {[
                "做一个15秒卖咖啡的竖屏短视频，清新治愈风",
                "用这张产品图做一条30秒卖点展示，保持产品一致",
                "一个数字人口播，介绍新款耳机，30秒",
              ].map((eg) => (
                <button key={eg} className="chat-eg" onClick={() => setText(eg)}>
                  {eg}
                </button>
              ))}
            </div>
          </div>
        )}
        {chat.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.assets && m.assets.length > 0 && (
              <div className="msg-thumbs">
                {m.assets.map((a, j) => (a.url ? <img key={j} src={a.url} /> : <span key={j} className="thumb-name">{a.name}</span>))}
              </div>
            )}
            <div className="msg-text">{m.text}</div>
            {m.plan && (
              <button className="apply-btn" onClick={() => applyPlan(m.plan!, m.assets)}>
                ⚡ 生成到画布
              </button>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant"><span className="spinner" /> 正在构思分镜…</div>}
      </div>

      {assets.length > 0 && (
        <div className="chat-attach">
          {assets.map((a, i) => (
            <div className="attach-item" key={i}>
              {a.url ? <img src={a.url} /> : <span>{a.name}</span>}
              <button onClick={() => setAssets((prev) => prev.filter((_, j) => j !== i))}>✕</button>
            </div>
          ))}
        </div>
      )}

      <div className="chat-input">
        <label className="attach-btn" title="附参考图">
          {uploading ? "…" : "📎"}
          <input type="file" accept="image/*" multiple style={{ display: "none" }} onChange={(e) => onPick(e.target.files)} />
        </label>
        <textarea
          value={text}
          placeholder="描述想法，可粘贴/拖入参考图…（Enter 发送，Shift+Enter 换行）"
          rows={2}
          onChange={(e) => setText(e.target.value)}
          onPaste={onPaste}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="run" disabled={busy} onClick={send}>
          发送
        </button>
      </div>
    </div>
  );
}
