import React, { useMemo, useCallback } from 'react';
import { Group, Line, Shape } from 'react-konva';
import { useGraphStore, type GraphEdge } from '../utils/graph-store';
import { calculateEdgePath } from '../utils/edge-utils';

interface CallEdgeObjectProps {
  edge: GraphEdge;
}

const SYMBOL_NODE_WIDTH = 140;
const SYMBOL_NODE_HEIGHT = 50;

export const CallEdgeObject: React.FC<CallEdgeObjectProps> = ({ edge }) => {
  const {
    symbolNodes,
    selectEdge,
    selectedEdgeId,
    hoveredNodeId,
  } = useGraphStore();

  const fromSymbol = symbolNodes.find((s) => s.id === edge.from);
  const toSymbol = symbolNodes.find((s) => s.id === edge.to);

  const isSelected = selectedEdgeId === edge.id;

  // Check if either endpoint is hovered
  const isEndpointHovered = hoveredNodeId === edge.from || hoveredNodeId === edge.to;

  // Get node bounds for edge calculation
  const fromNode = useMemo(() => {
    if (!fromSymbol) return null;
    return {
      x: fromSymbol.x,
      y: fromSymbol.y,
      width: SYMBOL_NODE_WIDTH,
      height: SYMBOL_NODE_HEIGHT,
    };
  }, [fromSymbol]);

  const toNode = useMemo(() => {
    if (!toSymbol) return null;
    return {
      x: toSymbol.x,
      y: toSymbol.y,
      width: SYMBOL_NODE_WIDTH,
      height: SYMBOL_NODE_HEIGHT,
    };
  }, [toSymbol]);

  // Calculate edge path
  const { path, arrowPoints } = useMemo(() => {
    if (!fromNode || !toNode) {
      return { path: '', arrowPoints: [] };
    }

    return calculateEdgePath(fromNode, toNode, {
      curved: true,
    });
  }, [fromNode, toNode]);

  const handleClick = useCallback(() => {
    selectEdge(edge.id);
  }, [edge.id, selectEdge]);

  // Don't render if nodes don't exist
  if (!fromNode || !toNode || !path) {
    return null;
  }

  // Edge opacity based on selection state
  const opacity = isSelected || isEndpointHovered ? 1 : 0.6;
  const strokeWidth = isSelected || isEndpointHovered ? 2.5 : 1.5;

  return (
    <Group onClick={handleClick}>
      {/* Glow effect */}
      <Line
        points={parsePathToPoints(path)}
        stroke="rgba(255, 193, 7, 0.3)"
        strokeWidth={strokeWidth + 4}
        lineCap="round"
        lineJoin="round"
        listening={false}
        perfectDrawEnabled={false}
      />

      {/* Main edge line */}
      <Line
        points={parsePathToPoints(path)}
        stroke={`rgba(255, 193, 7, ${opacity})`}
        strokeWidth={strokeWidth}
        dash={[5, 5]}
        lineCap="round"
        lineJoin="round"
        perfectDrawEnabled={false}
      />

      {/* Arrow head */}
      {arrowPoints.length === 3 && (
        <Shape
          sceneFunc={(context, shape) => {
            context.beginPath();
            context.moveTo(arrowPoints[0].x, arrowPoints[0].y);
            context.lineTo(arrowPoints[1].x, arrowPoints[1].y);
            context.lineTo(arrowPoints[2].x, arrowPoints[2].y);
            context.closePath();
            context.fillStrokeShape(shape);
          }}
          fill={`rgba(255, 193, 7, ${opacity})`}
          stroke={`rgba(255, 193, 7, ${opacity})`}
          strokeWidth={1}
          perfectDrawEnabled={false}
        />
      )}
    </Group>
  );
};

/**
 * Parse SVG path string to array of points for Konva Line
 * Simple parser for M x y L x y Q cx cy x y format
 */
function parsePathToPoints(path: string): number[] {
  const points: number[] = [];
  const commands = path.match(/[MLQC]\s*[\d.-]+\s*[\d.-]+/g);

  if (!commands) return points;

  for (const cmd of commands) {
    const parts = cmd.split(/[\s,]+/);
    const coords = parts.slice(1).map(parseFloat);

    // For simplicity, just extract the endpoints
    // For Q command, use the final point
    if (parts[0] === 'Q' && coords.length >= 4) {
      points.push(coords[2], coords[3]);
    } else if (coords.length >= 2) {
      points.push(coords[0], coords[1]);
    }
  }

  return points;
}

export default CallEdgeObject;
