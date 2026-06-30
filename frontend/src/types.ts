// 后端 /object_info 返回的节点定义结构。

export type InputSpec = [string | string[], Record<string, any>];

export interface NodeDef {
  name: string;
  category: string;
  input: {
    required?: Record<string, InputSpec>;
    optional?: Record<string, InputSpec>;
  };
  output: string[];        // RETURN_TYPES
  output_name: string[];   // RETURN_NAMES
  output_node: boolean;
  is_cloud_task: boolean;
}

export type ObjectInfo = Record<string, NodeDef>;

// 画布节点的 data 负载
export interface GraphNodeData {
  classType: string;
  def: NodeDef;
  values: Record<string, any>;   // 各 widget 的当前值（未连线时生效）
  status?: string; // idle | queued | executing | done | cached | error
  preview?: { type: string; url?: string; value?: string }[];
  pinned?: boolean;
  error?: string;
}

// 凭据：按厂商存
export interface Creds {
  api_key: string;
  workspace_id?: string;
}
export type CredsMap = Record<string, Creds>;
