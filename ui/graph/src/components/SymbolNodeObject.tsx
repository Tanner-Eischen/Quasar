import React, { useCallback, useMemo } from 'react';
import { Group, Rect, Text } from 'react-konva';
import { KonvaEventObject } from 'konva/lib/Node';
import { useGraphStore, type SymbolNode } from '../utils/graph-store';

interface SymbolNodeObjectProps {
  node: SymbolNode;
}

const NODE_WIDTH = 140;
const NODE_HEIGHT = 50;
const PADDING = 10;

// Color mapping for symbol kinds
const KIND_COLORS: Record<string, { fill: string; stroke: string }> = {
  SUBROUTINE: { fill: '#4169E1', stroke: '#6495ED' },
  FUNCTION: { fill: '#228B22', stroke: '#32CD32' },
  PROGRAM: { fill: '#8B4513', stroke: '#CD853F' },
  MODULE: { fill: '#9400D3', stroke: '#BA55D3' },
  COMMON: { fill: '#708090', stroke: '#A9A9A9' },
};

const DEFAULT_COLOR = { fill: '#4169E1', stroke: '#6495ED' };

export const SymbolNodeObject: React.FC<SymbolNodeObjectProps> = ({ node }) => {
  const {
    selectedNodeId,
    hoveredNodeId,
    selectNode,
    hoverNode,
    openSourcePanel,
    updateNodePosition,
  } = useGraphStore();

  const isSelected = selectedNodeId === node.id;
  const isHovered = hoveredNodeId === node.id;

  const colors = KIND_COLORS[node.kind] || DEFAULT_COLOR;

  const handleClick = useCallback(() => {
    selectNode(node.id);
    openSourcePanel(node.id);
  }, [node.id, selectNode, openSourcePanel]);

  const handleMouseEnter = useCallback(() => {
    hoverNode(node.id);
    document.body.style.cursor = 'pointer';
  }, [node.id, hoverNode]);

  const handleMouseLeave = useCallback(() => {
    hoverNode(null);
    document.body.style.cursor = 'default';
  }, [hoverNode]);

  const handleDragEnd = useCallback(
    (e: KonvaEventObject<DragEvent>) => {
      updateNodePosition(node.id, e.target.x(), e.target.y());
    },
    [node.id, updateNodePosition]
  );

  // Truncate name if too long
  const displayName = useMemo(() => {
    if (node.name.length > 16) {
      return node.name.substring(0, 14) + '...';
    }
    return node.name;
  }, [node.name]);

  // Scale for hover/selected state
  const scale = isHovered || isSelected ? 1.05 : 1;
  const width = NODE_WIDTH * scale;
  const height = NODE_HEIGHT * scale;

  return (
    <Group
      x={node.x}
      y={node.y}
      draggable
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onDragEnd={handleDragEnd}
    >
      {/* Main rectangle */}
      <Rect
        x={-width / 2}
        y={-height / 2}
        width={width}
        height={height}
        fill={colors.fill}
        stroke={isSelected ? '#FFFFFF' : colors.stroke}
        strokeWidth={isSelected ? 2 : 1.5}
        cornerRadius={4}
        shadowColor="#000000"
        shadowBlur={isHovered || isSelected ? 12 : 6}
        shadowOpacity={0.4}
        shadowOffsetY={2}
        perfectDrawEnabled={false}
      />

      {/* Symbol name */}
      <Text
        text={displayName}
        x={-width / 2 + PADDING}
        y={-height / 2 + 8}
        width={width - PADDING * 2}
        align="center"
        fontSize={12}
        fontFamily="Inter, sans-serif"
        fontStyle="600"
        fill="#FFFFFF"
        listening={false}
        ellipsis={true}
        wrap="none"
      />

      {/* Kind label */}
      <Text
        text={node.kind}
        x={-width / 2 + PADDING}
        y={-height / 2 + 24}
        width={width - PADDING * 2}
        align="center"
        fontSize={9}
        fontFamily="Inter, sans-serif"
        fill="rgba(255, 255, 255, 0.7)"
        listening={false}
      />

      {/* Kind indicator dot */}
      <Rect
        x={-width / 2 + 4}
        y={-height / 2 + 4}
        width={6}
        height={6}
        fill={colors.stroke}
        cornerRadius={3}
        perfectDrawEnabled={false}
      />
    </Group>
  );
};

export default SymbolNodeObject;
