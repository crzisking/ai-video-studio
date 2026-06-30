# -*- coding: utf-8 -*-
"""阿里百炼 DashScope 适配。
- 文本/图像走业务空间域名(北京)：https://{ws}.cn-beijing.maas.aliyuncs.com/api/v1，留空回退普通域名
- 视频走普通域名：https://dashscope.aliyuncs.com/api/v1
"""


def ws_base(workspace_id: str) -> str:
    if workspace_id:
        return f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1"
    return "https://dashscope.aliyuncs.com/api/v1"
