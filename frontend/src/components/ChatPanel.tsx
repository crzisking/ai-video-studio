import { useState } from "react";
import { useStore } from "../store";

// AI 对话面板：描述需求 → AI 出分镜方案 → 一键生成到画布。
export default function ChatPanel() {
  const chat = useStore((s) => s.chat);
  const busy = useStore((s) => s.agentBusy);
  const sendAgentMessage = useStore((s) => s.sendAgentMessage);
  const applyPlan = useStore((s) => s.applyPlan);
  const [text, setText] = useState("");
  const [open, setOpen] = useState(true);
  const [max, setMax] = useState(false);

  const send = () => {
    const m = text.trim();
    if (!m || busy) return;
    setText("");
    sendAgentMessage(m);
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

      <div className="chat-body">
        {chat.length === 0 && (
          <div className="chat-empty">
            描述你想要的短视频，我来出分镜方案并连好节点图。
            <div className="chat-egs">
              {[
                "做一个15秒卖咖啡的竖屏短视频，清新治愈风",
                "3个镜头的旅行vlog片头，海边日出到城市夜景",
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
            <div className="msg-text">{m.text}</div>
            {m.plan && (
              <button className="apply-btn" onClick={() => applyPlan(m.plan!)}>
                ⚡ 生成到画布
              </button>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant"><span className="spinner" /> 正在构思分镜…</div>}
      </div>

      <div className="chat-input">
        <textarea
          value={text}
          placeholder="描述你的视频想法…（Enter 发送，Shift+Enter 换行）"
          rows={2}
          onChange={(e) => setText(e.target.value)}
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
