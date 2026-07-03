// 节点/端口的新手提示（人话版）。key = 节点类名。
export interface NodeHint {
  desc: string;
  inputs?: Record<string, string>;
}

export const NODE_HINTS: Record<string, NodeHint> = {
  ProviderNode: {
    desc: "选一个 AI 厂商。把它的输出连给任何需要 provider 的节点，那个节点才知道用谁生成。",
    inputs: {
      provider: "aliyun=阿里百炼，volcano=火山方舟。密钥在顶部「🔑凭据」里填。",
    },
  },
  TextNode: {
    desc: "一段文本。可当提示词复用，连给多个节点的文本输入。",
    inputs: { text: "随便写一段文字，会输出给下游。" },
  },
  GenImage: {
    desc: "文字生成图片：填一句画面描述，出一张图。",
    inputs: {
      provider: "连 ProviderNode。",
      prompt: "想要的画面，越具体越好（主体+动作+光线+风格）。",
      ratio: "画面比例，竖屏短视频常用 9:16。",
      seed: "随机种子。同种子+同提示=同一张图；改数字换一张。",
      refs: "可选：参考主体图，让角色/物体保持一致（连 LoadReference）。",
      init_image: "可选：以这张图为基础改（首帧→尾帧就靠它）。",
    },
  },
  TTS: {
    desc: "文字转语音：把文本读成一段音频（阿里线）。",
    inputs: {
      provider: "连 ProviderNode（阿里）。",
      text: "要朗读的文稿。",
      voice: "音色名，如 longxiaochun_v2；或连 CloneVoice 用复刻的声音。",
    },
  },
  CloneVoice: {
    desc: "声音复刻：上传一段参考音频（10秒~1分钟、人声清晰），输出专属音色，接到 TTS 的 voice 上。同一段音频只注册一次（缓存）。",
    inputs: {
      provider: "连 ProviderNode（阿里）。",
      name: "参考音频文件名，点「＋上传」选音频自动填。",
    },
  },
  LoadReference: {
    desc: "导入本地素材（图片/主体参考）。点「＋上传」选文件，输出参考主体给下游。",
    inputs: { paths: "上传的文件名，一行一个。用右侧「＋上传」自动填。" },
  },
  LoadImage: {
    desc: "加载一张已上传的图片，输出普通图像。可直接接数字人肖像、视频首帧、图生图底图。",
    inputs: { name: "上传后的文件名（uploads/ 里那个）。" },
  },
  VideoI2V: {
    desc: "图生视频：给一张首帧图，按运动描述生成一段视频。可再给尾帧做首尾帧过渡。",
    inputs: {
      provider: "连 ProviderNode。",
      first: "首帧图（连 GenImage 的输出）。",
      motion: "镜头/主体怎么动，如“镜头缓慢推进，人物转身”。",
      duration: "时长（秒），2–15。",
      ratio: "画面比例。",
      resolution: "清晰度，720P/1080P。",
      last: "可选：尾帧图，做首尾帧过渡。",
      audio: "可选：配音音频，贴到视频上。",
    },
  },
  VideoR2V: {
    desc: "参考生视频：给参考主体，直接按运动描述生成视频，保持角色一致（仅阿里）。",
    inputs: {
      provider: "连 ProviderNode（阿里）。",
      refs: "参考主体（连 LoadReference）。",
      motion: "主体怎么动。",
      duration: "时长（秒）。",
      ratio: "画面比例。",
      resolution: "清晰度。",
    },
  },
  Avatar: {
    desc: "数字人：给一张人像 + 一段音频，生成对口型说话视频（仅阿里）。",
    inputs: {
      provider: "连 ProviderNode（阿里）。",
      portrait: "人像图（连 GenImage 或 LoadReference）。",
      audio: "说话音频（连 TTS）。",
      resolution: "清晰度。",
    },
  },
  ConcatVideos: {
    desc: "把多段视频按顺序拼成一条完整成片。video_1 起，依次接 video_2、3…",
    inputs: {
      video_1: "第 1 段视频（必填）。",
      video_2: "第 2 段（可选）。",
      video_3: "第 3 段（可选）。",
    },
  },
  PreviewImage: {
    desc: "预览一张图片（终端节点）。",
    inputs: { image: "连任意图像输出。" },
  },
  Preview: {
    desc: "通用预览终点：图片/视频/音频接哪个就播哪个。任何工作流都用它收尾。",
    inputs: {
      image: "连图像输出。",
      video: "连视频输出。",
      audio: "连音频输出。",
    },
  },
};
