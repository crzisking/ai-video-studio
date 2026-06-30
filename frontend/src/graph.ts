import type { Edge, Node } from "reactflow";
import type { GraphNodeData, NodeDef, ObjectInfo } from "./types";

// socket 类型 → 颜色（连线与端口上色，类型即语义）
export const SOCKET_COLOR: Record<string, string> = {
  TEXT: "#9ccc65",
  IMAGE: "#42a5f5",
  VIDEO: "#ab47bc",
  AUDIO: "#ffa726",
  IMAGE_REF: "#26c6da",
  PROVIDER: "#ef5350",
  PERSONA: "#ec407a",
  STORYBOARD: "#8d6e63",
  SHOT: "#bdbdbd",
  INT: "#78909c",
  FLOAT: "#78909c",
  BOOLEAN: "#78909c",
};
export function socketColor(t: string): string {
  return SOCKET_COLOR[t] || "#90a4ae";
}

// 节点头部强调色（按 category）
const CATEGORY_ACCENT: Record<string, string> = {
  基础: "#ef5350",
  图像: "#42a5f5",
  视频: "#ab47bc",
  音频: "#ffa726",
  输入: "#26c6da",
  输出: "#26a69a",
};
export function categoryAccent(cat: string): string {
  return CATEGORY_ACCENT[cat] || "#78909c";
}

// 这些类型在未连线时用 widget 编辑；其余类型必须靠连线
const WIDGET_TYPES = new Set(["TEXT", "INT", "FLOAT", "BOOLEAN"]);
export function isWidgetType(t: string | string[]): boolean {
  if (Array.isArray(t)) return true; // COMBO 下拉
  return WIDGET_TYPES.has(t);
}

// 输入声明的"连线类型"：list(COMBO) 视为 TEXT 语义
export function declType(t: string | string[]): string {
  return Array.isArray(t) ? "COMBO" : t;
}

// 连线类型兼容（与后端 types_compatible 对齐）
export function compatible(fromType: string, toDecl: string | string[]): boolean {
  if (Array.isArray(toDecl)) return true; // 下拉一般接 TEXT
  if (toDecl === "*" || fromType === "*") return true;
  return fromType === toDecl;
}

export function allInputs(def: NodeDef): [string, [string | string[], any]][] {
  return [
    ...Object.entries(def.input.required || {}),
    ...Object.entries(def.input.optional || {}),
  ];
}

// 把 reactflow 图序列化成后端 Prompt JSON
export function serialize(
  nodes: Node<GraphNodeData>[],
  edges: Edge[]
): { nodes: Record<string, any> } {
  // 建立：目标节点+输入名 → [源节点id, 源输出槽位]
  const linkByTarget: Record<string, [string, number]> = {};
  for (const e of edges) {
    const inName = (e.targetHandle || "").replace(/^in:/, "");
    const slot = parseInt((e.sourceHandle || "out:0").replace(/^out:/, ""), 10);
    linkByTarget[`${e.target}::${inName}`] = [e.source, slot];
  }

  const out: Record<string, any> = {};
  for (const n of nodes) {
    const def = n.data.def;
    const inputs: Record<string, any> = {};
    for (const [name, spec] of allInputs(def)) {
      const link = linkByTarget[`${n.id}::${name}`];
      if (link) {
        inputs[name] = link;
      } else if (name in (n.data.values || {})) {
        let v = n.data.values[name];
        const t = spec[0];
        if (!Array.isArray(t) && (t === "INT" || t === "FLOAT")) v = Number(v);
        inputs[name] = v;
      }
    }
    out[n.id] = { class_type: n.data.classType, inputs };
  }
  return { nodes: out };
}

// 节点初始 widget 值（用 default）
export function defaultValues(def: NodeDef): Record<string, any> {
  const values: Record<string, any> = {};
  for (const [name, spec] of allInputs(def)) {
    const [t, opts] = spec;
    if (Array.isArray(t)) values[name] = opts.default ?? t[0];
    else if (t === "INT" || t === "FLOAT") values[name] = opts.default ?? 0;
    else if (t === "BOOLEAN") values[name] = opts.default ?? false;
    else if (t === "TEXT") values[name] = opts.default ?? "";
  }
  return values;
}
