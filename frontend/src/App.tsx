import { useEffect, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  type Connection,
} from "reactflow";
import "reactflow/dist/style.css";
import { useStore } from "./store";
import { fetchObjectInfo, connectWS } from "./api";
import { allInputs, categoryAccent, compatible } from "./graph";
import { STARTER_KEY } from "./templates";
import { loadAutosave, saveAutosave, serializeGraph } from "./storage";
import DynamicNode from "./components/DynamicNode";
import Sidebar from "./components/Sidebar";
import Toolbar from "./components/Toolbar";
import Legend from "./components/Legend";
import ChatPanel from "./components/ChatPanel";
import "./styles.css";

export default function App() {
  return (
    <ReactFlowProvider>
      <Editor />
    </ReactFlowProvider>
  );
}

function Editor() {
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, setObjectInfo, applyWsEvent } =
    useStore();
  const nodeTypes = useMemo(() => ({ dynamic: DynamicNode }), []);

  useEffect(() => {
    fetchObjectInfo()
      .then((oi) => {
        setObjectInfo(oi);
        const st = useStore.getState();
        if (st.nodes.length > 0) return;
        // 优先恢复上次自动保存的图；没有才加载入门模板
        const saved = loadAutosave();
        if (saved && saved.nodes?.length) st.loadSavedGraph(saved);
        else st.loadTemplate(STARTER_KEY);
      })
      .catch((e) => console.error(e));
    const ws = connectWS(applyWsEvent);
    return () => ws.close();
  }, []);

  // 自动保存：图变动后防抖写入 localStorage
  useEffect(() => {
    if (nodes.length === 0 && edges.length === 0) return;
    const t = setTimeout(() => saveAutosave(serializeGraph(nodes, edges)), 500);
    return () => clearTimeout(t);
  }, [nodes, edges]);

  // 类型安全连线：源输出类型 vs 目标输入声明类型
  const isValidConnection = (c: Connection): boolean => {
    const { nodes, objectInfo } = useStore.getState();
    const src = nodes.find((n) => n.id === c.source);
    const tgt = nodes.find((n) => n.id === c.target);
    if (!src || !tgt) return false;
    const slot = parseInt((c.sourceHandle || "out:0").replace(/^out:/, ""), 10);
    const fromType = objectInfo[src.data.classType]?.output[slot];
    const inName = (c.targetHandle || "").replace(/^in:/, "");
    const toSpec = allInputs(objectInfo[tgt.data.classType]).find(([n]) => n === inName);
    if (!fromType || !toSpec) return false;
    return compatible(fromType, toSpec[1][0]);
  };

  return (
    <div className="app">
      <Toolbar />
      <div className="main">
        <Sidebar />
        <div className="canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            isValidConnection={isValidConnection}
            defaultEdgeOptions={{ type: "smoothstep", animated: true }}
            deleteKeyCode={["Backspace", "Delete"]}
            minZoom={0.2}
            fitView
            fitViewOptions={{ padding: 0.25, maxZoom: 0.9 }}
          >
            <Background color="#2c2e34" gap={18} size={1.5} />
            <Controls />
            <MiniMap
              pannable
              zoomable
              maskColor="rgba(0,0,0,0.55)"
              nodeColor={(n) => categoryAccent((n.data as any)?.def?.category || "")}
            />
          </ReactFlow>
          {nodes.length === 0 && (
            <div className="empty-hint">
              <div className="big">画布是空的</div>
              <div>点顶部「📋 模板」选一条完整工作流，或从左侧添加节点</div>
            </div>
          )}
          <Legend />
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
