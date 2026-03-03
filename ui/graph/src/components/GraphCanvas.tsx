import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import { Stage, Layer } from 'react-konva';
import { KonvaEventObject } from 'konva/lib/Node';
import {
  useGraphStore,
  selectVisibleNodes,
  selectVisibleEdges,
  FileNode,
  SymbolNode as SymbolNodeType,
} from '../utils/graph-store';
import { FileNodeObject } from './FileNodeObject';
import { SymbolNodeObject } from './SymbolNodeObject';
import { CallEdgeObject } from './CallEdgeObject';
import { SourceCodePanel } from './SourceCodePanel';

const MIN_SCALE = 0.1;
const MAX_SCALE = 4;
const SCALE_BY = 1.1;

export const GraphCanvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<any>(null);

  const [dimensions, setDimensions] = React.useState({ width: 1200, height: 900 });

  const viewportX = useGraphStore((state) => state.viewportX);
  const viewportY = useGraphStore((state) => state.viewportY);
  const viewportScale = useGraphStore((state) => state.viewportScale);
  const loading = useGraphStore((state) => state.loading);
  const error = useGraphStore((state) => state.error);
  const nodes = useGraphStore((state) => state.nodes);
  const symbolNodes = useGraphStore((state) => state.symbolNodes);
  const edges = useGraphStore((state) => state.edges);
  const stats = useGraphStore((state) => state.stats);

  const fetchGraph = useGraphStore((state) => state.fetchGraph);
  const setViewport = useGraphStore((state) => state.setViewport);
  const resetView = useGraphStore((state) => state.resetView);

  // Calculate visible nodes and edges
  const visibleNodes = useMemo(() => {
    const result: (FileNode | SymbolNodeType)[] = [
      ...nodes.filter((n): n is FileNode => n.type === 'file'),
    ];

    nodes.forEach((node) => {
      if (node.type === 'file' && node.expanded) {
        const fileSymbols = symbolNodes.filter(
          (s) => s.fileNodeId === node.id
        );
        result.push(...fileSymbols);
      }
    });

    return result;
  }, [nodes, symbolNodes]);

  const visibleEdges = useMemo(() => {
    const expandedFileIds = new Set(
      nodes
        .filter((n): n is FileNode => n.type === 'file' && n.expanded)
        .map((n) => n.id)
    );

    return edges.filter((edge) => {
      const fromSymbol = symbolNodes.find((s) => s.id === edge.from);
      const toSymbol = symbolNodes.find((s) => s.id === edge.to);

      const fromExpanded = fromSymbol && expandedFileIds.has(fromSymbol.fileNodeId);
      const toExpanded = toSymbol && expandedFileIds.has(toSymbol.fileNodeId);

      return fromExpanded || toExpanded;
    });
  }, [nodes, symbolNodes, edges]);

  // Fetch graph data on mount
  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Handle wheel zoom
  const handleWheel = useCallback(
    (e: KonvaEventObject<WheelEvent>) => {
      e.evt.preventDefault();

      const stage = stageRef.current;
      if (!stage) return;

      const oldScale = viewportScale;
      const pointer = stage.getPointerPosition();
      if (!pointer) return;

      const mousePointTo = {
        x: (pointer.x - viewportX) / oldScale,
        y: (pointer.y - viewportY) / oldScale,
      };

      const direction = e.evt.deltaY < 0 ? 1 : -1;
      const newScale =
        direction > 0
          ? Math.min(oldScale * SCALE_BY, MAX_SCALE)
          : Math.max(oldScale / SCALE_BY, MIN_SCALE);

      const newPos = {
        x: pointer.x - mousePointTo.x * newScale,
        y: pointer.y - mousePointTo.y * newScale,
      };

      setViewport(newPos.x, newPos.y, newScale);
    },
    [viewportScale, viewportX, viewportY, setViewport]
  );

  // Handle drag
  const handleDragEnd = useCallback(
    (e: KonvaEventObject<DragEvent>) => {
      const stage = e.target;
      if (stage === stageRef.current) {
        setViewport(stage.x(), stage.y(), viewportScale);
      }
    },
    [viewportScale, setViewport]
  );

  // Handle zoom controls
  const zoomIn = useCallback(() => {
    const newScale = Math.min(viewportScale * SCALE_BY, MAX_SCALE);
    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;

    const mousePointTo = {
      x: (centerX - viewportX) / viewportScale,
      y: (centerY - viewportY) / viewportScale,
    };

    setViewport(
      centerX - mousePointTo.x * newScale,
      centerY - mousePointTo.y * newScale,
      newScale
    );
  }, [viewportScale, viewportX, viewportY, dimensions, setViewport]);

  const zoomOut = useCallback(() => {
    const newScale = Math.max(viewportScale / SCALE_BY, MIN_SCALE);
    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;

    const mousePointTo = {
      x: (centerX - viewportX) / viewportScale,
      y: (centerY - viewportY) / viewportScale,
    };

    setViewport(
      centerX - mousePointTo.x * newScale,
      centerY - mousePointTo.y * newScale,
      newScale
    );
  }, [viewportScale, viewportX, viewportY, dimensions, setViewport]);

  if (error) {
    return (
      <div className="graph-container">
        <div className="loading-overlay">
          <div style={{ textAlign: 'center', color: '#F85149' }}>
            <div style={{ fontSize: '18px', marginBottom: '8px' }}>Error Loading Graph</div>
            <div style={{ color: '#8B949E' }}>{error}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-container" ref={containerRef}>
      {loading && (
        <div className="loading-overlay">
          <div style={{ textAlign: 'center' }}>
            <div className="loading-spinner" />
            <div className="loading-text">Loading graph...</div>
          </div>
        </div>
      )}

      <Stage
        ref={stageRef}
        width={dimensions.width}
        height={dimensions.height}
        x={viewportX}
        y={viewportY}
        scaleX={viewportScale}
        scaleY={viewportScale}
        draggable
        onWheel={handleWheel}
        onDragEnd={handleDragEnd}
      >
        <Layer>
          {/* Render edges first (below nodes) */}
          {visibleEdges.map((edge) => (
            <CallEdgeObject key={edge.id} edge={edge} />
          ))}

          {/* Render file nodes */}
          {visibleNodes
            .filter((node): node is FileNode => node.type === 'file')
            .map((node) => (
              <FileNodeObject key={node.id} node={node} />
            ))}

          {/* Render symbol nodes */}
          {visibleNodes
            .filter((node): node is SymbolNodeType => node.type === 'symbol')
            .map((node) => (
              <SymbolNodeObject key={node.id} node={node} />
            ))}
        </Layer>
      </Stage>

      {/* Controls */}
      <div className="graph-controls">
        <button className="control-button" onClick={zoomIn} title="Zoom In">
          +
        </button>
        <button className="control-button" onClick={zoomOut} title="Zoom Out">
          −
        </button>
        <button className="control-button" onClick={resetView} title="Reset View">
            ⌂
        </button>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-value">{stats.fileCount}</div>
            <div className="stat-label">Files</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{stats.symbolCount}</div>
            <div className="stat-label">Symbols</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{stats.callCount}</div>
            <div className="stat-label">Calls</div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="graph-legend">
        <div className="legend-title">Legend</div>
        <div className="legend-item">
          <div className="legend-icon file" />
          <span>File (double-click to expand)</span>
        </div>
        <div className="legend-item">
          <div className="legend-icon symbol" />
          <span>Symbol (click for source)</span>
        </div>
        <div className="legend-item">
          <div className="legend-icon edge" />
          <span>Call reference</span>
        </div>
      </div>

      {/* Source Code Panel */}
      <SourceCodePanel />
    </div>
  );
};

export default GraphCanvas;
