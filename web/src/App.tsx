import { useEffect, useState } from "react";

// 通过 Vite 代理走相对路径 → FastAPI :8000（免 CORS）
async function api(path: string, opts: RequestInit = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const t = await r.text();
  let j: any = null;
  try { j = t ? JSON.parse(t) : null; } catch { throw new Error("HTTP " + r.status); }
  if (!r.ok) throw new Error(j?.detail || j?.error || "HTTP " + r.status);
  return j;
}

type Project = { id: number; name: string; type: string; provider: string; video_engine: string; status: string };

export default function App() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState("promo");
  const [provider, setProvider] = useState("aliyun");
  const [engine, setEngine] = useState("r2v");
  const [err, setErr] = useState("");

  async function load() {
    try {
      await api("/health"); setOnline(true);
      setProjects(await api("/projects"));
    } catch (e: any) { setOnline(false); setErr(e.message); }
  }
  useEffect(() => { load(); }, []);

  async function create() {
    if (!name.trim()) return alert("请填项目名");
    try {
      await api("/projects", { method: "POST", body: JSON.stringify({ name, type, provider, video_engine: engine }) });
      setName(""); load();
    } catch (e: any) { setErr(e.message); }
  }
  async function del(id: number) {
    if (!confirm("删除此项目？")) return;
    await api(`/projects/${id}`, { method: "DELETE" }); load();
  }

  return (
    <div className="wrap">
      <h1>AI 短视频生成平台 <span style={{ color: "var(--mut)", fontSize: 14, fontWeight: 400 }}>· React + FastAPI</span></h1>
      <div className="sub">
        后端：{online === null ? "检测中…" : online ? <span className="ok">已连接 (代理 → :8000)</span> : <span className="err">未连接，请先启动后端 uvicorn</span>}
      </div>

      <div className="card">
        <div className="lbl">新建项目</div>
        <div className="row">
          <div><div className="lbl">项目名</div><input value={name} onChange={e => setName(e.target.value)} placeholder="如：XX公司宣传片" /></div>
          <div><div className="lbl">产品线</div>
            <select value={type} onChange={e => setType(e.target.value)}>
              <option value="promo">企业宣传</option><option value="drama">短剧</option>
            </select></div>
        </div>
        <div className="row">
          <div><div className="lbl">AI 厂商</div>
            <select value={provider} onChange={e => setProvider(e.target.value)}>
              <option value="aliyun">阿里百炼</option><option value="volcano">火山方舟</option>
            </select></div>
          <div><div className="lbl">视频引擎</div>
            <select value={engine} onChange={e => setEngine(e.target.value)}>
              <option value="r2v">参考生视频 r2v</option><option value="i2v">首尾帧 i2v</option>
            </select></div>
        </div>
        <button onClick={create}>创建项目</button>
      </div>

      {err && <div className="card err">{err}</div>}

      <div className="card">
        <div className="lbl">项目列表</div>
        {projects.length === 0 && <div style={{ color: "var(--mut)" }}>还没有项目</div>}
        {projects.map(p => (
          <div className="proj" key={p.id}>
            <div>
              <b>{p.name}</b>{" "}
              <span className="pill">{p.type === "drama" ? "短剧" : "企业宣传"}</span>
              <span className="pill">{p.provider}</span>
              <span className="pill">{p.video_engine}</span>
              <span className="pill">{p.status}</span>
            </div>
            <button style={{ background: "#2a323d" }} onClick={() => del(p.id)}>删除</button>
          </div>
        ))}
      </div>
    </div>
  );
}
