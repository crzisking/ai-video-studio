import type { Edge, Node } from "reactflow";
import type { GraphNodeData, ObjectInfo } from "./types";
import { build, type EdgeSpec, type NodeSpec } from "./templates";

// 后端 /agent/plan 返回的方案结构
export interface Shot {
  type: "i2v" | "first_last" | "r2v" | "avatar";
  prompt?: string;
  prompt_last?: string;
  motion?: string;
  duration?: number;
  portrait_prompt?: string;
  script?: string;
}
export interface Plan {
  title?: string;
  provider?: "aliyun" | "volcano";
  aspect?: string;
  shots: Shot[];
  narration_text?: string;
  voice?: string;
  use_refs?: boolean;
  portrait_edit?: string; // 对用户照片做图生图加工（换背景/增强）的指令
  summary?: string;
}

// 方案 → 节点图（确定性拼装，保证合法）。refNames = 用户上传的参考图文件名。
export function compilePlan(
  plan: Plan,
  oi: ObjectInfo,
  refNames: string[] = []
): { nodes: Node<GraphNodeData>[]; edges: Edge[] } {
  const nodes: NodeSpec[] = [];
  const edges: EdgeSpec[] = [];
  const ratio = plan.aspect || "9:16";
  const provider = plan.provider || "aliyun";

  const COL = 380;
  const baseY = 260;

  // 共享的厂商节点
  nodes.push({ id: "prov", type: "ProviderNode", pos: [40, baseY], values: { provider } });

  // 需要参考主体？（use_refs 或含 r2v 镜头）
  // 只有会被真正接线时才创建 LoadReference：有 r2v 镜头，或 use_refs+有图+存在场景出图(GenImage)消费它
  const hasSceneGen = plan.shots.some((s) => s.type === "i2v" || s.type === "first_last");
  const needRef =
    plan.shots.some((s) => s.type === "r2v") ||
    (!!plan.use_refs && refNames.length > 0 && hasSceneGen);
  if (needRef)
    nodes.push({
      id: "ref",
      type: "LoadReference",
      pos: [40, baseY + 220],
      values: { paths: refNames.join("\n") },
    });

  // 用户上传了人物照片 → 数字人肖像直接用照片（共享一个 LoadImage）
  const hasAvatarShot = plan.shots.some((s) => s.type === "avatar");
  const usePhotoPortrait = hasAvatarShot && refNames.length > 0;
  // 有 portrait_edit 时插一步图生图：照片 → GenImage(换背景/增强) → 肖像
  const editPortrait = usePhotoPortrait && !!(plan.portrait_edit || "").trim();
  let portraitSrc = "pimg"; // 数字人肖像的来源节点
  if (usePhotoPortrait) {
    nodes.push({
      id: "pimg",
      type: "LoadImage",
      pos: [40, baseY - 220],
      values: { name: refNames[0] },
    });
    if (editPortrait) {
      nodes.push({
        id: "pedit",
        type: "GenImage",
        pos: [40, baseY - 480],
        values: { prompt: plan.portrait_edit || "", ratio },
      });
      edges.push(["prov", 0, "pedit", "provider"], ["pimg", 0, "pedit", "init_image"]);
      portraitSrc = "pedit";
    }
  }

  const videoIds: string[] = []; // 各镜头产出视频的节点 id
  // use_refs 时场景出图也挂参考主体，保持人物/产品一致（LoadReference 不再空挂）
  const wireSceneRefs = needRef && refNames.length > 0;

  plan.shots.forEach((s, i) => {
    const x = 340 + i * COL;
    const pre = `s${i}`;
    if (s.type === "first_last") {
      const g1 = `${pre}_g1`, g2 = `${pre}_g2`, vi = `${pre}_vi`;
      nodes.push({ id: g1, type: "GenImage", pos: [x, 40], values: { prompt: s.prompt || "", ratio } });
      nodes.push({ id: g2, type: "GenImage", pos: [x, 360], values: { prompt: s.prompt_last || "", ratio } });
      nodes.push({ id: vi, type: "VideoI2V", pos: [x + 200, 200], values: { motion: s.motion || "", duration: s.duration || 5, ratio } });
      edges.push(["prov", 0, g1, "provider"], ["prov", 0, g2, "provider"], ["prov", 0, vi, "provider"]);
      edges.push([g1, 0, g2, "init_image"], [g1, 0, vi, "first"], [g2, 0, vi, "last"]);
      if (wireSceneRefs) edges.push(["ref", 0, g1, "refs"], ["ref", 0, g2, "refs"]);
      videoIds.push(vi);
    } else if (s.type === "r2v") {
      const vr = `${pre}_vr`;
      nodes.push({ id: vr, type: "VideoR2V", pos: [x, baseY], values: { motion: s.motion || "", duration: s.duration || 5, ratio } });
      edges.push(["prov", 0, vr, "provider"], ["ref", 0, vr, "refs"]);
      videoIds.push(vr);
    } else if (s.type === "avatar") {
      const t = `${pre}_t`, av = `${pre}_av`;
      nodes.push({ id: t, type: "TTS", pos: [x, 360], values: { text: s.script || "", voice: plan.voice || "longxiaochun_v2" } });
      nodes.push({ id: av, type: "Avatar", pos: [x + 200, 200] });
      edges.push(["prov", 0, t, "provider"], ["prov", 0, av, "provider"]);
      if (usePhotoPortrait) {
        // 用户照片（或其图生图加工版）当肖像
        edges.push([portraitSrc, 0, av, "portrait"]);
      } else {
        const p = `${pre}_p`;
        nodes.push({ id: p, type: "GenImage", pos: [x, 40], values: { prompt: s.portrait_prompt || "", ratio } });
        edges.push(["prov", 0, p, "provider"], [p, 0, av, "portrait"]);
      }
      edges.push([t, 0, av, "audio"]);
      videoIds.push(av);
    } else {
      // i2v（默认）
      const g = `${pre}_g`, vi = `${pre}_vi`;
      nodes.push({ id: g, type: "GenImage", pos: [x, 80], values: { prompt: s.prompt || "", ratio } });
      nodes.push({ id: vi, type: "VideoI2V", pos: [x + 200, 220], values: { motion: s.motion || "", duration: s.duration || 5, ratio } });
      edges.push(["prov", 0, g, "provider"], ["prov", 0, vi, "provider"], [g, 0, vi, "first"]);
      if (wireSceneRefs) edges.push(["ref", 0, g, "refs"]);
      videoIds.push(vi);
    }
  });

  const tailX = 340 + plan.shots.length * COL;

  // 视频汇总
  let videoOut: [string, number] | null = null;
  if (videoIds.length === 1) {
    videoOut = [videoIds[0], 0];
  } else if (videoIds.length > 1) {
    nodes.push({ id: "concat", type: "ConcatVideos", pos: [tailX, baseY] });
    videoIds.slice(0, 8).forEach((vid, i) => edges.push([vid, 0, "concat", `video_${i + 1}`]));
    videoOut = ["concat", 0];
  }

  // 预览终点
  const previewId = "preview";
  nodes.push({ id: previewId, type: "Preview", pos: [tailX + 360, baseY] });
  if (videoOut) edges.push([videoOut[0], videoOut[1], previewId, "video"]);

  // 全片旁白（无 avatar 时单独出一条音频接到同一个 Preview）
  const hasAvatar = plan.shots.some((s) => s.type === "avatar");
  if (plan.narration_text && !hasAvatar) {
    nodes.push({ id: "narr", type: "TTS", pos: [tailX, baseY + 220], values: { text: plan.narration_text, voice: plan.voice || "longxiaochun_v2" } });
    edges.push(["prov", 0, "narr", "provider"], ["narr", 0, previewId, "audio"]);
  }

  return build(oi, nodes, edges);
}
