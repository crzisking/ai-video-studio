import type { Edge, Node } from "reactflow";
import type { GraphNodeData, ObjectInfo } from "./types";

// 存储层：把画布图序列化进 localStorage（自动保存 + 命名工作流库）。
// 只存必要字段（不存 def，加载时按 classType 从 objectInfo 重挂）。

interface SavedNode {
  id: string;
  position: { x: number; y: number };
  classType: string;
  values: Record<string, any>;
  pinned?: boolean;
}
export interface SavedGraph {
  nodes: SavedNode[];
  edges: Pick<Edge, "id" | "source" | "sourceHandle" | "target" | "targetHandle">[];
}
export interface SavedWorkflow {
  id: string;
  name: string;
  ts: number;
  graph: SavedGraph;
}

const AUTOSAVE_KEY = "avs.autosave";
const LIB_KEY = "avs.workflows";

export function serializeGraph(nodes: Node<GraphNodeData>[], edges: Edge[]): SavedGraph {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      position: n.position,
      classType: n.data.classType,
      values: n.data.values || {},
      pinned: n.data.pinned,
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      sourceHandle: e.sourceHandle,
      target: e.target,
      targetHandle: e.targetHandle,
    })),
  };
}

export function deserializeGraph(
  g: SavedGraph,
  oi: ObjectInfo
): { nodes: Node<GraphNodeData>[]; edges: Edge[] } {
  const nodes = (g.nodes || [])
    .filter((n) => oi[n.classType])
    .map((n) => ({
      id: n.id,
      type: "dynamic",
      position: n.position,
      data: {
        classType: n.classType,
        def: oi[n.classType],
        values: n.values || {},
        pinned: n.pinned,
        status: "idle",
      },
    })) as Node<GraphNodeData>[];
  const edges = (g.edges || []).map((e) => ({ ...e, type: "smoothstep", animated: true })) as Edge[];
  return { nodes, edges };
}

// —— 自动保存 ——
export function saveAutosave(g: SavedGraph) {
  try {
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(g));
  } catch {
    /* 配额满等，忽略 */
  }
}
export function loadAutosave(): SavedGraph | null {
  try {
    const s = localStorage.getItem(AUTOSAVE_KEY);
    return s ? JSON.parse(s) : null;
  } catch {
    return null;
  }
}

// —— 命名工作流库 ——
export function listWorkflows(): SavedWorkflow[] {
  try {
    return JSON.parse(localStorage.getItem(LIB_KEY) || "[]");
  } catch {
    return [];
  }
}
function writeLib(list: SavedWorkflow[]) {
  localStorage.setItem(LIB_KEY, JSON.stringify(list));
}
export function saveWorkflow(name: string, g: SavedGraph, ts: number): SavedWorkflow {
  const list = listWorkflows();
  const existing = list.find((w) => w.name === name);
  const wf: SavedWorkflow = existing
    ? { ...existing, ts, graph: g }
    : { id: "wf_" + ts.toString(36), name, ts, graph: g };
  const next = existing ? list.map((w) => (w.id === wf.id ? wf : w)) : [wf, ...list];
  writeLib(next);
  return wf;
}
export function deleteWorkflow(id: string) {
  writeLib(listWorkflows().filter((w) => w.id !== id));
}
