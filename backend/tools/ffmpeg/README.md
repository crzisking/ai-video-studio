# ffmpeg（拼接成片用，ConcatVideos 节点依赖）

ffmpeg 的 exe 体积大（~100MB），**不入 git**（见根目录 .gitignore）。
每台机器各自准备一份即可。后端按以下**优先级自动查找**（任一命中即用，无需改代码）：

1. **项目内置**：把 `ffmpeg.exe`（可选 `ffprobe.exe`）放到本目录 `backend/tools/ffmpeg/`
2. **环境变量**：`FFMPEG_PATH` 指向某个 `ffmpeg.exe`
3. **系统 PATH**：`ffmpeg` 在 PATH 里（如 `winget install Gyan.FFmpeg`）
4. **常见位置**：winget Links、Gyan 包目录、`C:\ffmpeg\**\ffmpeg.exe`

## 最省事的做法（免安装、免管理员）

下载 Windows 静态构建（单 exe，不依赖 DLL），解压后把 `bin\ffmpeg.exe` 丢进本目录：

- gyan.dev：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
- 解压 → 复制 `ffmpeg-*-essentials_build\bin\ffmpeg.exe` 到 `backend/tools/ffmpeg/`

验证：`backend\tools\ffmpeg\ffmpeg.exe -version` 能打印版本即可，重启后端后 ConcatVideos 就能用。

> 需要 libx264 + aac 编码（essentials/full 构建都带）。
