import type { Edge, Node } from "reactflow";
import type { GraphNodeData, ObjectInfo } from "./types";
import { defaultValues } from "./graph";

export type NodeSpec = { id: string; type: string; pos: [number, number]; values?: Record<string, any> };
export type EdgeSpec = [string, number, string, string]; // [源节点, 源槽位, 目标节点, 目标输入名]

export function build(oi: ObjectInfo, nodes: NodeSpec[], edges: EdgeSpec[]): { nodes: Node<GraphNodeData>[]; edges: Edge[] } {
  const ns = nodes
    .filter((n) => oi[n.type])
    .map((n) => ({
      id: n.id,
      type: "dynamic",
      position: { x: n.pos[0], y: n.pos[1] },
      data: {
        classType: n.type,
        def: oi[n.type],
        values: { ...defaultValues(oi[n.type]), ...(n.values || {}) },
        status: "idle",
      },
    })) as Node<GraphNodeData>[];
  const es = edges.map((e, i) => ({
    id: `e${i}`,
    source: e[0],
    sourceHandle: `out:${e[1]}`,
    target: e[2],
    targetHandle: `in:${e[3]}`,
    type: "smoothstep",
    animated: true,
  })) as Edge[];
  return { nodes: ns, edges: es };
}

export interface Template {
  key: string;
  name: string;
  desc: string;
  make: (oi: ObjectInfo) => { nodes: Node<GraphNodeData>[]; edges: Edge[] };
}

export const TEMPLATES: Template[] = [
  {
    key: "t2i",
    name: "文生图 → 预览",
    desc: "最简单的一条：选厂商 → 出一张图 → 预览。先用这条熟悉连线。",
    make: (oi) =>
      build(
        oi,
        [
          { id: "p", type: "ProviderNode", pos: [40, 240], values: { provider: "aliyun" } },
          { id: "g", type: "GenImage", pos: [320, 80], values: { prompt: "一只戴墨镜的柴犬，电影感打光，4k" } },
          { id: "v", type: "Preview", pos: [760, 180] },
        ],
        [
          ["p", 0, "g", "provider"],
          ["g", 0, "v", "image"],
        ]
      ),
  },
  {
    key: "i2v",
    name: "首尾帧生视频",
    desc: "出首帧→以首帧为参考出尾帧→首尾帧生成一段视频→预览。",
    make: (oi) =>
      build(
        oi,
        [
          { id: "p", type: "ProviderNode", pos: [40, 360], values: { provider: "aliyun" } },
          { id: "g1", type: "GenImage", pos: [300, 40], values: { prompt: "海边日出，空镜，电影感" } },
          { id: "g2", type: "GenImage", pos: [300, 380], values: { prompt: "海边正午，阳光强烈，电影感" } },
          { id: "vi", type: "VideoI2V", pos: [700, 200], values: { motion: "镜头缓慢推进，时间流逝" } },
          { id: "v", type: "Preview", pos: [1060, 240] },
        ],
        [
          ["p", 0, "g1", "provider"],
          ["p", 0, "g2", "provider"],
          ["p", 0, "vi", "provider"],
          ["g1", 0, "g2", "init_image"],
          ["g1", 0, "vi", "first"],
          ["g2", 0, "vi", "last"],
          ["vi", 0, "v", "video"],
        ]
      ),
  },
  {
    key: "tts",
    name: "配音 → 预览",
    desc: "文本转语音，输出音频并预览。",
    make: (oi) =>
      build(
        oi,
        [
          { id: "p", type: "ProviderNode", pos: [40, 200], values: { provider: "aliyun" } },
          { id: "t", type: "TTS", pos: [320, 100], values: { text: "大家好，欢迎来到本期节目。", voice: "longxiaochun_v2" } },
          { id: "v", type: "Preview", pos: [720, 160] },
        ],
        [
          ["p", 0, "t", "provider"],
          ["t", 0, "v", "audio"],
        ]
      ),
  },
  {
    key: "r2v",
    name: "参考生视频（角色一致）",
    desc: "上传参考主体 → 按运动描述生成视频，保持角色一致（仅阿里）。",
    make: (oi) =>
      build(
        oi,
        [
          { id: "p", type: "ProviderNode", pos: [40, 240], values: { provider: "aliyun" } },
          { id: "lr", type: "LoadReference", pos: [300, 80] },
          { id: "vr", type: "VideoR2V", pos: [640, 180], values: { motion: "人物自然走动，环顾四周" } },
          { id: "v", type: "Preview", pos: [1000, 220] },
        ],
        [
          ["p", 0, "vr", "provider"],
          ["lr", 0, "vr", "refs"],
          ["vr", 0, "v", "video"],
        ]
      ),
  },
];

export const STARTER_KEY = "t2i";
