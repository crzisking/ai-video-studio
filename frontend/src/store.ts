import { create } from "zustand";
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "reactflow";
import type { CredsMap, GraphNodeData, ObjectInfo } from "./types";
import { defaultValues, serialize } from "./graph";
import { submitPrompt, requestPlan } from "./api";
import { TEMPLATES } from "./templates";
import { compilePlan, type Plan } from "./compiler";
import { deserializeGraph, saveWorkflow, serializeGraph, type SavedGraph } from "./storage";

export interface Asset {
  name: string;
  url?: string;
}
export interface ChatMsg {
  role: "user" | "assistant" | "error";
  text: string;
  plan?: Plan;
  assets?: Asset[];
}

let _id = 1;
const nextId = () => String(_id++);

interface State {
  objectInfo: ObjectInfo;
  nodes: Node<GraphNodeData>[];
  edges: Edge[];
  creds: CredsMap;
  promptId: string | null;
  queueRemaining: number;
  runError: string | null;

  setObjectInfo: (oi: ObjectInfo) => void;
  setCreds: (provider: string, c: { api_key: string; workspace_id?: string }) => void;
  onNodesChange: (c: NodeChange[]) => void;
  onEdgesChange: (c: EdgeChange[]) => void;
  onConnect: (c: Connection) => void;
  addNodeOfType: (classType: string, pos?: { x: number; y: number }) => void;
  updateNodeValue: (id: string, name: string, value: any) => void;
  deleteNode: (id: string) => void;
  loadTemplate: (key: string) => void;
  clearGraph: () => void;
  loadSavedGraph: (g: SavedGraph) => void;
  saveCurrentWorkflow: (name: string) => void;
  togglePin: (id: string) => void;
  applyWsEvent: (msg: any) => void;
  run: () => Promise<void>;
  rerunNode: (id: string) => Promise<void>;

  chat: ChatMsg[];
  agentBusy: boolean;
  sendAgentMessage: (message: string, assets?: Asset[]) => Promise<void>;
  applyPlan: (plan: Plan, assets?: Asset[]) => void;
}

export const useStore = create<State>((set, get) => ({
  objectInfo: {},
  nodes: [],
  edges: [],
  creds: {},
  promptId: null,
  queueRemaining: 0,
  runError: null,
  chat: [],
  agentBusy: false,

  setObjectInfo: (oi) => set({ objectInfo: oi }),
  setCreds: (provider, c) => set((s) => ({ creds: { ...s.creds, [provider]: c } })),

  onNodesChange: (c) => set((s) => ({ nodes: applyNodeChanges(c, s.nodes) })),
  onEdgesChange: (c) => set((s) => ({ edges: applyEdgeChanges(c, s.edges) })),
  onConnect: (c) =>
    set((s) => ({
      // 一个输入端口只接一条线：先删旧的同目标连线
      edges: addEdge(
        c,
        s.edges.filter((e) => !(e.target === c.target && e.targetHandle === c.targetHandle))
      ),
    })),

  addNodeOfType: (classType, pos) => {
    const def = get().objectInfo[classType];
    if (!def) return;
    // 错开落点，避免新节点叠在一起
    const n = get().nodes.length;
    const position = pos ?? { x: 80 + (n % 5) * 80, y: 60 + (n % 5) * 70 + Math.floor(n / 5) * 40 };
    const node: Node<GraphNodeData> = {
      id: nextId(),
      type: "dynamic",
      position,
      data: { classType, def, values: defaultValues(def), status: "idle" },
    };
    set((s) => ({ nodes: [...s.nodes, node] }));
  },

  updateNodeValue: (id, name, value) =>
    set((s) => ({
      nodes: s.nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, values: { ...n.data.values, [name]: value } } } : n
      ),
    })),

  deleteNode: (id) =>
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.source !== id && e.target !== id),
    })),

  loadTemplate: (key) => {
    const { objectInfo } = get();
    const tpl = TEMPLATES.find((t) => t.key === key);
    if (!tpl) return;
    const g = tpl.make(objectInfo);
    // 避免后续新增节点 id 与模板 id 冲突
    _id = Math.max(_id, 1000);
    set({ nodes: g.nodes, edges: g.edges, promptId: null, runError: null });
  },

  clearGraph: () => set({ nodes: [], edges: [], promptId: null, runError: null }),

  loadSavedGraph: (g) => {
    const { objectInfo } = get();
    const graph = deserializeGraph(g, objectInfo);
    _id = Math.max(_id, 1000);
    set({ nodes: graph.nodes, edges: graph.edges, promptId: null, runError: null });
  },

  saveCurrentWorkflow: (name) => {
    const { nodes, edges } = get();
    saveWorkflow(name, serializeGraph(nodes, edges), Date.now());
  },

  togglePin: (id) =>
    set((s) => ({
      nodes: s.nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, pinned: !n.data.pinned } } : n
      ),
    })),

  applyWsEvent: (msg) => {
    const { type, data } = msg;
    if (!data) return;
    const nodeId: string | undefined = data.node;
    const patch = (id: string, p: Partial<GraphNodeData>) =>
      set((s) => ({
        nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...p } } : n)),
      }));

    // —— 全局事件（无 node 字段）先处理 ——
    if (type === "queued") {
      set({ queueRemaining: data.remaining ?? 0, runError: null });
      return;
    }
    if (type === "execution_done") {
      // 收尾：还挂着 queued/executing 的（未参与执行的孤立节点）归位 idle
      set((s) => ({
        nodes: s.nodes.map((n) =>
          n.data.status === "queued" || n.data.status === "executing"
            ? { ...n, data: { ...n.data, status: "idle" } }
            : n
        ),
      }));
      return;
    }
    if (type === "execution_error") {
      set((s) => ({
        runError: data.error || "执行出错",
        nodes: s.nodes.map((n) =>
          n.data.status === "queued" || n.data.status === "executing"
            ? { ...n, data: { ...n.data, status: "idle" } }
            : n
        ),
      }));
      return;
    }

    // —— 节点级事件 ——
    if (!nodeId) return;
    switch (type) {
      case "executing":
        patch(nodeId, { status: "executing", error: undefined });
        break;
      case "cached":
        patch(nodeId, { status: "cached" });
        break;
      case "executed":
        // outputs 为空（如 Preview 这类终端节点）时不要覆盖已收到的 preview
        patch(nodeId, {
          status: "done",
          ...(data.outputs && data.outputs.length ? { preview: data.outputs } : {}),
        });
        break;
      case "preview":
      case "final":
        patch(nodeId, { status: "done", preview: [{ type: data.type || "video", url: data.url }] });
        break;
      case "node_error":
        patch(nodeId, { status: "error", error: data.error });
        break;
    }
  },

  run: async () => {
    const { nodes, edges, creds } = get();
    try {
      set({ runError: null });
      // 运行前清掉非 pin 节点的旧状态（pin 的靠缓存命中"不动它"）
      set((s) => ({
        nodes: s.nodes.map((n) => ({ ...n, data: { ...n.data, status: n.data.pinned ? n.data.status : "queued" } })),
      }));
      const resp = await submitPrompt(serialize(nodes, edges), creds, []);
      set({ promptId: resp.prompt_id, queueRemaining: resp.queue_remaining });
    } catch (e: any) {
      set({ runError: String(e.message || e) });
    }
  },

  rerunNode: async (id) => {
    const { nodes, edges, creds } = get();
    try {
      set({ runError: null });
      const resp = await submitPrompt(serialize(nodes, edges), creds, [id]);
      set({ promptId: resp.prompt_id, queueRemaining: resp.queue_remaining });
    } catch (e: any) {
      set({ runError: String(e.message || e) });
    }
  },

  sendAgentMessage: async (message, assets = []) => {
    const { creds, chat } = get();
    // 选一个已填 key 的厂商，默认 aliyun（规划器 = 该厂商的文本模型）
    const provider = creds.aliyun?.api_key ? "aliyun" : creds.volcano?.api_key ? "volcano" : "aliyun";
    // 多轮：回喂上一版方案；这轮没传图则沿用之前传过的图
    const lastPlanMsg = [...chat].reverse().find((m) => m.plan);
    if (assets.length === 0) {
      const lastAssetsMsg = [...chat].reverse().find((m) => m.assets && m.assets.length > 0);
      assets = lastAssetsMsg?.assets || [];
    }
    set((s) => ({ chat: [...s.chat, { role: "user", text: message, assets }], agentBusy: true }));
    try {
      const plan: Plan = await requestPlan(message, creds, provider, assets, lastPlanMsg?.plan);
      const lines = (plan.shots || [])
        .map((sh, i) => `${i + 1}. [${sh.type}] ${sh.prompt || sh.portrait_prompt || sh.script || ""}`)
        .join("\n");
      const text = `📋 ${plan.title || "方案"}（${plan.aspect}）\n${plan.summary || ""}\n\n分镜：\n${lines}`;
      set((s) => ({ chat: [...s.chat, { role: "assistant", text, plan, assets }], agentBusy: false }));
    } catch (e: any) {
      set((s) => ({ chat: [...s.chat, { role: "error", text: String(e.message || e) }], agentBusy: false }));
    }
  },

  applyPlan: (plan, assets = []) => {
    const { objectInfo } = get();
    const refNames = assets.map((a) => a.name).filter(Boolean);
    const g = compilePlan(plan, objectInfo, refNames);
    _id = Math.max(_id, 1000);
    set({ nodes: g.nodes, edges: g.edges, promptId: null, runError: null });
  },
}));

// 开发调试：把 store 暴露到 window，便于排查
if (typeof window !== "undefined") (window as any).__store = useStore;
