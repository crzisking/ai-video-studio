import { useState } from "react";
import { useStore } from "../store";

// 凭据按厂商录入。凭据走 /prompt 请求体注入、不进图、不进缓存。
export default function CredsPanel() {
  const creds = useStore((s) => s.creds);
  const setCreds = useStore((s) => s.setCreds);
  const [open, setOpen] = useState(false);

  return (
    <div className="creds">
      <button onClick={() => setOpen((v) => !v)}>🔑 凭据 {open ? "▲" : "▼"}</button>
      {open && (
        <div className="creds-body">
          {["aliyun", "volcano"].map((p) => (
            <div key={p} className="creds-row">
              <b>{p === "aliyun" ? "阿里百炼" : "火山方舟"}</b>
              <input
                placeholder="api_key"
                value={creds[p]?.api_key || ""}
                onChange={(e) => setCreds(p, { ...creds[p], api_key: e.target.value })}
              />
              {p === "aliyun" && (
                <input
                  placeholder="workspace_id（可选）"
                  value={creds[p]?.workspace_id || ""}
                  onChange={(e) => setCreds(p, { ...(creds[p] || { api_key: "" }), workspace_id: e.target.value })}
                />
              )}
            </div>
          ))}
          <small>凭据仅随生成请求发送，不会存进工作流 JSON。</small>
        </div>
      )}
    </div>
  );
}
