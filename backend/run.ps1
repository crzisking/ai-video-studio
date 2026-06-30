# 后端启动脚本（Windows PowerShell）—— uv 管理依赖
# 首次/更新依赖：在项目根目录执行  uv sync
# 启动（在 backend/ 目录执行）：
uv run --project .. uvicorn app.main:app --reload --port 8000
