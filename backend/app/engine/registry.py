# -*- coding: utf-8 -*-
"""节点注册表。等价 ComfyUI 的 NODE_CLASS_MAPPINGS + /object_info。

用法：
    @register
    class GenImage(NodeBase): ...

前端启动时拉 /object_info，拿到所有节点的 INPUT/RETURN 类型，据此画节点面板。
"""
from __future__ import annotations
from app.engine.node import NodeBase

NODE_REGISTRY: dict[str, type] = {}


def register(cls: type) -> type:
    name = cls.type_name()
    if name in NODE_REGISTRY:
        raise ValueError(f"节点重名: {name}")
    NODE_REGISTRY[name] = cls
    return cls


def get_node_class(class_type: str) -> type:
    if class_type not in NODE_REGISTRY:
        raise KeyError(f"未知节点类型: {class_type}")
    return NODE_REGISTRY[class_type]


def object_info() -> dict:
    """导出全部节点定义给前端。"""
    return {name: cls.describe() for name, cls in NODE_REGISTRY.items()}


def load_all_nodes() -> None:
    """导入 app.nodes 下所有模块以触发 @register。在 app 启动时调用一次。"""
    import importlib
    import pkgutil
    import app.nodes as nodes_pkg
    for _, modname, _ in pkgutil.iter_modules(nodes_pkg.__path__):
        importlib.import_module(f"app.nodes.{modname}")
