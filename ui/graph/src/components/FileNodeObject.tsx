import React, { useCallback, useMemo, useState } from 'react';
import { Group, Circle, Text, Rect } from 'react-konva';
import { KonvaEventObject } from 'konva/lib/Node';
import { useGraphStore, type FileNode } from '../utils/graph-store';

interface FileNodeObjectProps {
  node: FileNode;
}

const DEFAULT_NODE_SIZE = 34;
const DEFAULT_GLOW_LEVEL = 1;
const BADGE_OFFSET_X = 28;
const BADGE_OFFSET_Y = -28;
const BADGE_WIDTH = 28;
const BADGE_HEIGHT = 20;

export const FileNodeObject: React.FC<FileNodeObjectProps> = ({ node }) => {
  const {
    selectedNodeId,
    hoveredNodeId,
    selectNode,
    hoverNode,
    toggleFileExpanded,
    updateNodePosition,
  } = useGraphStore();

  const [isHoveredLocal, setIsHoveredLocal] = useState(false);

  const isSelected = selectedNodeId === node.id;
  const isHovered = hoveredNodeId === node.id;
  const expanded = node.expanded;

  // Node styling - golden proto-star
  const nodeSize = DEFAULT_NODE_SIZE;
  const glowLevel = DEFAULT_GLOW_LEVEL;

  const handleClick = useCallback(() => {
    selectNode(node.id);
  }, [node.id, selectNode]);

  const handleDblClick = useCallback(() => {
    toggleFileExpanded(node.id);
  }, [node.id, toggleFileExpanded]);

  const handleMouseEnter = useCallback(() => {
    setIsHoveredLocal(true);
    hoverNode(node.id);
    document.body.style.cursor = 'pointer';
  }, [node.id, hoverNode]);

  const handleMouseLeave = useCallback(() => {
    setIsHoveredLocal(false);
    hoverNode(null);
    document.body.style.cursor = 'default';
  }, [hoverNode]);

  const handleDragEnd = useCallback(
    (e: KonvaEventObject<DragEvent>) => {
      updateNodePosition(node.id, e.target.x(), e.target.y());
    },
    [node.id, updateNodePosition]
  );

  // Preview dots for hovered state (showing contained symbols)
  const previewDots = useMemo(() => {
    const count = Math.min(node.symbolCount, 24);
    const dots: Array<{ x: number; y: number; r: number; opacity: number }> = [];

    for (let i = 0; i < count; i++) {
      const angle = (i / Math.max(count, 1)) * Math.PI * 2;
      const ring = 1 + (i % 3) * 0.35;
      const radius = nodeSize * (1.7 + ring);
      dots.push({
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        r: 1.2 + (i % 3),
        opacity: 0.22 + (i % 4) * 0.08,
      });
    }
    return dots;
  }, [node.symbolCount, nodeSize]);

  return (
    <Group
      x={node.x}
      y={node.y}
      draggable
      onClick={handleClick}
      onDblClick={handleDblClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onDragEnd={handleDragEnd}
    >
      {/* Invisible hitbox for hover detection */}
      <Circle
        radius={nodeSize * 2.5 * glowLevel}
        fill="transparent"
        listening={true}
      />

      {/* Outer glow ring */}
      <Circle
        radius={nodeSize * 2.5 * glowLevel}
        fill="rgba(255, 215, 0, 0.03)"
        listening={false}
      />

      {/* Middle glow ring */}
      <Circle
        radius={nodeSize * 1.5 * glowLevel}
        fill="rgba(255, 215, 0, 0.08)"
        listening={false}
      />

      {/* Hover preview of contained items */}
      {(isHovered || isHoveredLocal) &&
        previewDots.map((dot, idx) => (
          <Circle
            key={`preview-dot-${node.id}-${idx}`}
            x={dot.x}
            y={dot.y}
            radius={dot.r}
            fill="rgba(255,255,255,0.85)"
            opacity={dot.opacity}
            listening={false}
          />
        ))}

      {/* Core glow */}
      <Circle
        radius={nodeSize}
        fill="rgba(255, 215, 0, 0.15)"
        listening={false}
      />

      {/* Bright center - the proto-star core */}
      <Circle
        radius={nodeSize * 0.5}
        fill="white"
        shadowColor="#FFD700"
        shadowBlur={20 * glowLevel}
        shadowOpacity={0.9}
        listening={false}
      />

      {/* Selection ring */}
      {isSelected && (
        <Circle
          radius={nodeSize * 1.8}
          stroke="#FFD700"
          strokeWidth={2}
          dash={[6, 3]}
          listening={false}
        />
      )}

      {/* File name */}
      <Text
        text={node.name}
        x={-70}
        y={nodeSize + 8}
        width={140}
        align="center"
        fontSize={12}
        fontFamily="Space Grotesk, sans-serif"
        fill="rgba(255, 255, 255, 0.6)"
        letterSpacing={1}
        listening={false}
      />

      {/* Symbol count badge */}
      {node.symbolCount > 0 && (
        <Group x={BADGE_OFFSET_X} y={BADGE_OFFSET_Y}>
          <Rect
            x={-BADGE_WIDTH / 2}
            y={-BADGE_HEIGHT / 2}
            width={BADGE_WIDTH}
            height={BADGE_HEIGHT}
            fill="rgba(10, 12, 20, 0.85)"
            stroke="rgba(255, 215, 0, 0.4)"
            strokeWidth={1}
            cornerRadius={4}
          />
          <Text
            text={String(node.symbolCount)}
            x={-BADGE_WIDTH / 2}
            y={-BADGE_HEIGHT / 2 + 4}
            width={BADGE_WIDTH}
            align="center"
            fontSize={11}
            fontFamily="Space Grotesk, sans-serif"
            fontWeight="600"
            fill="#FFD700"
            listening={false}
          />
        </Group>
      )}

      {/* Expanded indicator */}
      {expanded && (
        <Group y={nodeSize + 30}>
          <Circle
            radius={8}
            fill="rgba(255, 215, 0, 0.2)"
            stroke="rgba(255, 215, 0, 0.6)"
            strokeWidth={1.5}
          />
          <Text
            text="−"
            x={-8}
            y={-7}
            width={16}
            align="center"
            fontSize={14}
            fontFamily="Space Grotesk, sans-serif"
            fontWeight="600"
            fill="#FFD700"
            listening={false}
          />
        </Group>
      )}
    </Group>
  );
};

export default FileNodeObject;
