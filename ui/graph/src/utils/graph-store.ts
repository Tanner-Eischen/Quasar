import { create } from 'zustand';

// === Types ===

export interface FileNode {
  id: string;
  type: 'file';
  name: string;
  path: string;
  x: number;
  y: number;
  symbolCount: number;
  lineCount: number;
  expanded: boolean;
}

export interface SymbolNode {
  id: string;
  type: 'symbol';
  name: string;
  kind: string;
  fileId: number;
  fileNodeId: string;
  startLine: number;
  endLine: number;
  signature: string | null;
  x: number;
  y: number;
}

export type GraphNode = FileNode | SymbolNode;

export interface GraphEdge {
  id: string;
  type: 'call';
  from: string;
  to: string;
  fromFileId: number | null;
  toFileId: number;
  line: number;
  snippet: string | null;
}

export interface GraphStats {
  fileCount: number;
  symbolCount: number;
  callCount: number;
  corpusId: number;
  repoUrl: string;
}

export interface GraphData {
  nodes: FileNode[];
  symbolNodes: SymbolNode[];
  edges: GraphEdge[];
  stats: GraphStats;
}

interface GraphState {
  // Data
  nodes: GraphNode[];
  symbolNodes: SymbolNode[];
  edges: GraphEdge[];
  stats: GraphStats | null;

  // UI State
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  hoveredNodeId: string | null;
  sourcePanelOpen: boolean;
  sourceSymbolId: string | null;
  loading: boolean;
  error: string | null;

  // Viewport
  viewportX: number;
  viewportY: number;
  viewportScale: number;

  // Actions
  fetchGraph: (corpusId?: number) => Promise<void>;
  updateNodePosition: (nodeId: string, x: number, y: number) => void;
  toggleFileExpanded: (fileNodeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  selectEdge: (edgeId: string | null) => void;
  hoverNode: (nodeId: string | null) => void;
  openSourcePanel: (symbolId: string) => void;
  closeSourcePanel: () => void;
  setViewport: (x: number, y: number, scale: number) => void;
  resetView: () => void;
}

// === Layout Helpers ===

function gridLayout(
  symbols: SymbolNode[],
  centerX: number,
  centerY: number,
  cols: number = 4,
  cellWidth: number = 160,
  cellHeight: number = 70
): SymbolNode[] {
  return symbols.map((symbol, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    const offsetX = (col - (Math.min(symbols.length, cols) - 1) / 2) * cellWidth;
    const offsetY = (row - Math.floor(symbols.length / cols) / 2) * cellHeight;

    return {
      ...symbol,
      x: centerX + offsetX,
      y: centerY + offsetY,
    };
  });
}

// === Store ===

export const useGraphStore = create<GraphState>((set) => ({
  // Initial state
  nodes: [],
  symbolNodes: [],
  edges: [],
  stats: null,

  selectedNodeId: null,
  selectedEdgeId: null,
  hoveredNodeId: null,
  sourcePanelOpen: false,
  sourceSymbolId: null,
  loading: false,
  error: null,

  viewportX: 0,
  viewportY: 0,
  viewportScale: 1,

  // Actions
  fetchGraph: async (corpusId?: number) => {
    set({ loading: true, error: null });

    try {
      const url = corpusId
        ? `/api/v1/graph/${corpusId}`
        : '/api/v1/graph';

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch graph: ${response.statusText}`);
      }

      const data: GraphData = await response.json();

      set({
        nodes: data.nodes,
        symbolNodes: data.symbolNodes,
        edges: data.edges,
        stats: data.stats,
        loading: false,
      });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to load graph',
      });
    }
  },

  updateNodePosition: (nodeId: string, x: number, y: number) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, x, y } : node
      ),
    }));
  },

  toggleFileExpanded: (fileNodeId: string) => {
    set((state) => {
      const fileNode = state.nodes.find((n) => n.id === fileNodeId) as FileNode | undefined;
      if (!fileNode) return state;

      const expanded = !fileNode.expanded;

      if (expanded) {
        const fileSymbols = state.symbolNodes.filter(
          (s) => s.fileNodeId === fileNodeId
        );

        const positionedSymbols = gridLayout(
          fileSymbols,
          fileNode.x,
          fileNode.y
        );

        const updatedSymbolNodes = state.symbolNodes.map((s) =>
          s.fileNodeId === fileNodeId
            ? positionedSymbols.find((ps) => ps.id === s.id) || s
            : s
        );

        return {
          nodes: state.nodes.map((n) =>
            n.id === fileNodeId ? { ...n, expanded } : n
          ),
          symbolNodes: updatedSymbolNodes,
        };
      } else {
        return {
          nodes: state.nodes.map((n) =>
            n.id === fileNodeId ? { ...n, expanded } : n
          ),
        };
      }
    });
  },

  selectNode: (nodeId: string | null) => {
    set({ selectedNodeId: nodeId });
  },

  selectEdge: (edgeId: string | null) => {
    set({ selectedEdgeId: edgeId });
  },

  hoverNode: (nodeId: string | null) => {
    set({ hoveredNodeId: nodeId });
  },

  openSourcePanel: (symbolId: string) => {
    set({
      sourcePanelOpen: true,
      sourceSymbolId: symbolId,
    });
  },

  closeSourcePanel: () => {
    set({
      sourcePanelOpen: false,
      sourceSymbolId: null,
    });
  },

  setViewport: (x: number, y: number, scale: number) => {
    set({
      viewportX: x,
      viewportY: y,
      viewportScale: scale,
    });
  },

  resetView: () => {
    set({
      viewportX: 0,
      viewportY: 0,
      viewportScale: 1,
    });
  },
}));

// === Selectors ===

export const selectVisibleNodes = (state: GraphState): GraphNode[] => {
  const visibleNodes: GraphNode[] = [...state.nodes.filter((n) => n.type === 'file')];

  state.nodes.forEach((node) => {
    if (node.type === 'file' && node.expanded) {
      const fileSymbols = state.symbolNodes.filter(
        (s) => s.fileNodeId === node.id
      );
      visibleNodes.push(...fileSymbols);
    }
  });

  return visibleNodes;
};

export const selectVisibleEdges = (state: GraphState): GraphEdge[] => {
  const expandedFileIds = new Set(
    state.nodes
      .filter((n) => n.type === 'file' && (n as FileNode).expanded)
      .map((n) => (n as FileNode).id)
  );

  return state.edges.filter((edge) => {
    const fromSymbol = state.symbolNodes.find((s) => s.id === edge.from);
    const toSymbol = state.symbolNodes.find((s) => s.id === edge.to);

    const fromExpanded = fromSymbol && expandedFileIds.has(fromSymbol.fileNodeId);
    const toExpanded = toSymbol && expandedFileIds.has(toSymbol.fileNodeId);

    return fromExpanded || toExpanded;
  });
};

export const selectSymbolById = (state: GraphState, symbolId: string): SymbolNode | undefined => {
  return state.symbolNodes.find((s) => s.id === symbolId);
};
