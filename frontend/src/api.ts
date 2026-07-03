import type { ObjectInfo } from "./types";

export async function fetchObjectInfo(): Promise<ObjectInfo> {
  const r = await fetch("/object_info");
  if (!r.ok) throw new Error("拉取 object_info 失败");
  return r.json();
}

export interface PromptResp {
  prompt_id: string;
  queue_remaining: number;
}

export async function submitPrompt(
  prompt: any,
  creds: Record<string, any>,
  forceRerun: string[] = []
): Promise<PromptResp> {
  const r = await fetch("/prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, creds, force_rerun: forceRerun }),
  });
  if (!r.ok) {
    let msg = "提交失败";
    try {
      const j = await r.json();
      msg = j.detail || JSON.stringify(j);
    } catch {
      msg = (await r.text()) || msg;
    }
    throw new Error(msg);
  }
  return r.json();
}

export async function uploadFile(file: File): Promise<{ names: string[]; urls: string[] }> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/upload", { method: "POST", body: fd });
  if (!r.ok) throw new Error("上传失败");
  return r.json();
}

export async function requestPlan(
  message: string,
  creds: Record<string, any>,
  provider: string,
  assets: { name: string; url?: string }[],
  prevPlan?: any
): Promise<any> {
  const r = await fetch("/agent/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, creds, provider, assets, prev_plan: prevPlan ?? null }),
  });
  if (!r.ok) {
    let msg = "规划失败";
    try {
      msg = (await r.json()).detail || msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return r.json();
}

// WebSocket：实时事件回传
export function connectWS(onMessage: (msg: any) => void): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {
      /* ignore */
    }
  };
  return ws;
}
