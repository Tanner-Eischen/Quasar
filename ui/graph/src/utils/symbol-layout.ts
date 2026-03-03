/**
 * Layout utilities for positioning nodes in the graph
 */

export interface Point {
  x: number;
  y: number;
}

export interface LayoutNode {
  id: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
}

/**
 * Generate positions for nodes in a circular layout
 */
export function circularLayout(
  count: number,
  options: {
    radius?: number;
    centerX?: number;
    centerY?: number;
    startAngle?: number;
  } = {}
): Point[] {
  const {
    radius = 400,
    centerX = 600,
    centerY = 450,
    startAngle = -Math.PI / 2, // Start from top
  } = options;

  const positions: Point[] = [];

  for (let i = 0; i < count; i++) {
    const angle = (2 * Math.PI * i) / count + startAngle;
    positions.push({
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  }

  return positions;
}

/**
 * Generate positions for nodes in a grid layout
 */
export function gridLayout(
  count: number,
  options: {
    cols?: number;
    cellWidth?: number;
    cellHeight?: number;
    centerX?: number;
    centerY?: number;
    startX?: number;
    startY?: number;
  } = {}
): Point[] {
  const {
    cols = 4,
    cellWidth = 160,
    cellHeight = 70,
    centerX,
    centerY,
    startX,
    startY,
  } = options;

  const positions: Point[] = [];
  const rows = Math.ceil(count / cols);

  for (let i = 0; i < count; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);

    if (centerX !== undefined && centerY !== undefined) {
      // Center the grid around centerX, centerY
      const offsetX = (col - (Math.min(count, cols) - 1) / 2) * cellWidth;
      const offsetY = (row - (rows - 1) / 2) * cellHeight;

      positions.push({
        x: centerX + offsetX,
        y: centerY + offsetY,
      });
    } else {
      // Start from startX, startY (default to 0,0 if not provided)
      positions.push({
        x: (startX || 0) + col * cellWidth,
        y: (startY || 0) + row * cellHeight,
      });
    }
  }

  return positions;
}

/**
 * Generate positions for nodes in a radial layout (sunflower pattern)
 */
export function radialLayout(
  count: number,
  options: {
    centerX?: number;
    centerY?: number;
    radiusStep?: number;
    angleOffset?: number;
  } = {}
): Point[] {
  const {
    centerX = 600,
    centerY = 450,
    radiusStep = 80,
    angleOffset = Math.PI * (3 - Math.sqrt(5)), // Golden angle
  } = options;

  const positions: Point[] = [];

  for (let i = 0; i < count; i++) {
    const radius = radiusStep * Math.sqrt(i + 1);
    const angle = i * angleOffset;

    positions.push({
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  }

  return positions;
}

/**
 * Calculate the bounding box of a set of nodes
 */
export function calculateBounds(nodes: LayoutNode[]): {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
} {
  if (nodes.length === 0) {
    return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const node of nodes) {
    const hw = (node.width || 100) / 2;
    const hh = (node.height || 50) / 2;

    minX = Math.min(minX, node.x - hw);
    minY = Math.min(minY, node.y - hh);
    maxX = Math.max(maxX, node.x + hw);
    maxY = Math.max(maxY, node.y + hh);
  }

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

/**
 * Calculate the center point to fit all nodes in view
 */
export function calculateFitView(
  nodes: LayoutNode[],
  viewportWidth: number,
  viewportHeight: number,
  padding: number = 50
): { x: number; y: number; scale: number } {
  const bounds = calculateBounds(nodes);

  if (bounds.width === 0 || bounds.height === 0) {
    return { x: 0, y: 0, scale: 1 };
  }

  const scaleX = (viewportWidth - padding * 2) / bounds.width;
  const scaleY = (viewportHeight - padding * 2) / bounds.height;
  const scale = Math.min(scaleX, scaleY, 1); // Don't zoom in past 1:1

  const centerX = bounds.minX + bounds.width / 2;
  const centerY = bounds.minY + bounds.height / 2;

  return {
    x: viewportWidth / 2 - centerX * scale,
    y: viewportHeight / 2 - centerY * scale,
    scale,
  };
}
