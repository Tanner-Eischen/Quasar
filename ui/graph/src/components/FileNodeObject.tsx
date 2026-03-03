import React, { useCallback } from 'react';
import { Group, Circle, Text, Rect } from 'react-konva';
import { KonvaEventObject } from 'konva/lib/Node';
import { useGraphStore, type FileNode } from '../utils/graph-store';

interface FileNodeObjectProps {
  node: FileNode;
}

const FILE_NODE_RADIUS = 35;
const BADGE_OFFSET_X = 25;
const BADGE_OFFSET_Y = -25;
const BADGE_WIDTH = 24;
const BADGE_HEIGHT = 18;

export const FileNodeObject: React.FC<FileNodeObjectProps> = ({ node }) => {
  const {
    selectedNodeId,
    hoveredNodeId,
    selectNode,
    hoverNode,
    toggleFileExpanded,
    updateNodePosition,
  } = useGraphStore();

  const isSelected = selectedNodeId === node.id;
  const isHovered = hoveredNodeId === node.id;
  const expanded = node.expanded;

  const handleClick = useCallback(() => {
    selectNode(node.id);
  }, [node.id, selectNode]);

  const handleDblClick = useCallback(() => {
    toggleFileExpanded(node.id);
  }, [node.id, toggleFileExpanded]);

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

  // Colors for proto-star glow effect
  const coreColor = expanded ? '#FF9800' : '#FFC107';
  const glowColor = expanded ? 'rgba(255, 152, 0, 0.4)' : 'rgba(255, 193, 7, 0.4)';
  const outerGlowColor = expanded ? 'rgba(255, 152, 0, 0.2)' : 'rgba(255, 193, 7, 0.2)';

  // Scale for hover/selected state
  const scale = isHovered || isSelected ? 1.1 : 1;
  const radius = FILE_NODE_RADIUS * scale;

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
      {/* Outer glow corona (only when hovered/selected) */}
      {(isHovered || isSelected) && (
        <Circle
          radius={radius + 20}
          fill={outerGlowColor}
          perfectDrawEnabled={false}
        />
      )}

      {/* Inner glow corona */}
      <Circle
        radius={radius + 8}
        fill={glowColor}
        perfectDrawEnabled={false}
      />

      {/* Core circle */}
      <Circle
        radius={radius}
        fill={coreColor}
        stroke={isSelected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.3)'}
        strokeWidth={isSelected ? 2 : 1}
        shadowColor="#FFC107"
        shadowBlur={15}
        shadowOpacity={0.5}
        perfectDrawEnabled={false}
      />

      {/* File icon - simple document shape */}
      <Group y={-8}>
        <Rect
          x={-8}
          y={-10}
          width={16}
          height={20}
          fill="rgba(0, 0, 0, 0.3)"
          cornerRadius={2}
        />
        <Rect
          x={-6}
          y={-4}
          width={12}
          height={2}
          fill="rgba(255, 255, 255, 0.5)"
        />
        <Rect
          x={-6}
          y={0}
          width={8}
          height={2}
          fill="rgba(255, 255, 255, 0.5)"
        />
        <Rect
          x={-6}
          y={4}
          width={10}
          height={2}
          fill="rgba(255, 255, 255, 0.5)"
        />
      </Group>

      {/* File name */}
      <Text
        text={node.name}
        x={-50}
        y={radius + 12}
        width={100}
        align="center"
        fontSize={11}
        fontFamily="Inter, sans-serif"
        fill="#FFFFFF"
        fontStyle="500"
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
            fill="#2D3748"
            stroke="#4A5568"
            strokeWidth={1}
            cornerRadius={4}
          />
          <Text
            text={String(node.symbolCount)}
            x={-BADGE_WIDTH / 2}
            y={-BADGE_HEIGHT / 2}
            width={BADGE_WIDTH}
            height={BADGE_HEIGHT}
            align="center"
            verticalAlign="middle"
            fontSize={10}
            fontFamily="Inter, sans-serif"
            fontWeight="600"
            fill="#FFFFFF"
            listening={false}
          />
        </Group>
      )}

      {/* Expanded indicator */}
      {expanded && (
        <Circle
          x={0}
          y={radius + 30}
          radius={6}
          fill="#FF9800"
          stroke="#FFFFFF"
          strokeWidth={1}
        />
      )}
    </Group>
  );
};

export default FileNodeObject;
