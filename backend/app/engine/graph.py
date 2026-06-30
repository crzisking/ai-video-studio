# -*- coding: utf-8 -*-
"""图解析 / 校验 / 环检测 / 拓扑序。

Prompt JSON 格式（与 ComfyUI 同构）：
{
  "nodes": {
    "1": {"class_type": "ProviderNode", "inputs": {"provider": "aliyun"}},
    "3": {"class_type": "TextNode",     "inputs": {"text": "一只猫"}},
    "5": {"class_type": "GenImage",
          "inputs": {"provider": ["1", 0], "prompt": ["3", 0], "seed": 42}}
  }
}

input 的值两种形态：
  - 字面量（数字/字符串/bool/list）
  - 连线 [上游节点id(str), 上游输出槽位(int)]

校验在**入队前**完成（先校验后花钱）：类型存在、必填齐、连线类型兼容、无环。
"""
from __future__ import annotations
from dataclasses import dataclass
from app.engine.registry import get_node_class
from app.engine.types import types_compatible, ANY


class GraphError(Exception):
    pass


def _is_link(v) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], str) and isinstance(v[1], int)


@dataclass
class ParsedGraph:
    nodes: dict          # id -> {class_type, inputs}
    order: list          # 拓扑序的节点 id 列表
    deps: dict           # id -> set(上游 id)
    output_ids: list     # OUTPUT_NODE 的 id


def parse_and_validate(prompt: dict) -> ParsedGraph:
    nodes = prompt.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise GraphError("空图或格式错误：缺少 nodes")

    deps: dict[str, set] = {nid: set() for nid in nodes}
    output_ids: list[str] = []

    # 1) 每个节点：类型存在、必填齐、连线引用合法 + 类型兼容
    for nid, node in nodes.items():
        ct = node.get("class_type")
        try:
            cls = get_node_class(ct)
        except KeyError as e:
            raise GraphError(f"节点 {nid}: {e}")

        if cls.OUTPUT_NODE:
            output_ids.append(nid)

        spec = cls.INPUT_TYPES()
        required = spec.get("required", {})
        optional = spec.get("optional", {})
        all_spec = {**required, **optional}
        inputs = node.get("inputs", {})

        for rname in required:
            if rname not in inputs:
                raise GraphError(f"节点 {nid}({ct}) 缺少必填输入: {rname}")

        for iname, ival in inputs.items():
            if iname not in all_spec:
                raise GraphError(f"节点 {nid}({ct}) 有未知输入: {iname}")
            if _is_link(ival):
                up_id, slot = ival[0], ival[1]
                if up_id not in nodes:
                    raise GraphError(f"节点 {nid} 的输入 {iname} 连到不存在的节点 {up_id}")
                up_cls = get_node_class(nodes[up_id]["class_type"])
                if slot >= len(up_cls.RETURN_TYPES):
                    raise GraphError(f"节点 {nid} 的输入 {iname} 连到 {up_id} 越界槽位 {slot}")
                from_type = up_cls.RETURN_TYPES[slot]
                # 取本输入声明的类型；若 spec 用 list 表示 COMBO，则视为受限文本/枚举
                decl = all_spec[iname][0]
                to_type = ANY if isinstance(decl, list) else decl
                if not types_compatible(from_type, to_type):
                    raise GraphError(
                        f"节点 {nid} 的输入 {iname} 类型不兼容：上游给 {from_type}，需要 {to_type}")
                deps[nid].add(up_id)

    if not output_ids:
        raise GraphError("图里没有输出节点（OUTPUT_NODE），不知道要产出什么")

    # 2) 环检测 + 拓扑序（Kahn）
    order = _toposort(nodes.keys(), deps)
    return ParsedGraph(nodes=nodes, order=order, deps=deps, output_ids=output_ids)


def _toposort(ids, deps: dict) -> list:
    indeg = {nid: 0 for nid in ids}
    children: dict[str, list] = {nid: [] for nid in ids}
    for nid, ups in deps.items():
        for up in ups:
            children[up].append(nid)
            indeg[nid] += 1
    queue = [nid for nid in ids if indeg[nid] == 0]
    order = []
    while queue:
        n = queue.pop()
        order.append(n)
        for c in children[n]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if len(order) != len(indeg):
        cyc = [nid for nid, d in indeg.items() if d > 0]
        raise GraphError(f"图里有环，涉及节点: {cyc}")
    return order


def prune_to_outputs(g: ParsedGraph) -> set:
    """从输出节点反向可达集——只有这些需要执行（等价 ComfyUI 只算输出依赖的子图）。"""
    needed: set = set()
    stack = list(g.output_ids)
    while stack:
        n = stack.pop()
        if n in needed:
            continue
        needed.add(n)
        stack.extend(g.deps[n])
    return needed
