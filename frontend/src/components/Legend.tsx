import { useState } from "react";
import { socketColor } from "../graph";

// 端口颜色图例：解释每种颜色端口是什么数据类型。
const TYPES: [string, string][] = [
  ["PROVIDER", "厂商/凭据"],
  ["TEXT", "文本/提示词"],
  ["IMAGE", "图像"],
  ["IMAGE_REF", "参考主体"],
  ["VIDEO", "视频"],
  ["AUDIO", "音频"],
];

export default function Legend() {
  const [open, setOpen] = useState(true);
  return (
    <div className={`legend ${open ? "" : "collapsed"}`}>
      <div className="legend-head" onClick={() => setOpen((v) => !v)}>
        <span>端口颜色</span>
        <span>{open ? "▾" : "▸"}</span>
      </div>
      {open && (
        <div className="legend-body">
          {TYPES.map(([t, label]) => (
            <div className="legend-row" key={t}>
              <span className="sw" style={{ background: socketColor(t === "IMAGE_REF" ? "IMAGE_REF" : t) }} />
              <span>{label}</span>
            </div>
          ))}
          <div className="legend-tip">左口=输入 · 右口=输出 · 同色才能连</div>
        </div>
      )}
    </div>
  );
}
