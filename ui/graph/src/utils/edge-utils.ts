/**
 * Edge utilities for calculating connection points and paths
 */

import type { Point } from './symbol-layout';

export interface NodeBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Get the center point of a node
 */
export function getNodeCenter(node: NodeBounds): Point {
  return {
    x: node.x,
    y: node.y,
  };
}

/**
 * Calculate intersection point of a line from center to a point on the node's border
 */
export function getBorderPoint(
  node: NodeBounds,
  targetCenter: Point
): Point {
  const center = getNodeCenter(node);
  const dx = targetCenter.x - center.x;
  const dy = targetCenter.y - center.y;

  // Half dimensions
  const hw = node.width / 2;
  const hh = node.height / 2;

  // Handle edge case where nodes are at same position
  if (dx === 0 && dy === 0) {
    return { x: center.x + hw, y: center.y };
  }

  // Calculate intersection with rectangle border
  // Using parametric line equation
  const absDx = Math.abs(dx);
  const absDy = Math.abs(dy);

  let t: number;

  if (absDx / hw > absDy / hh) {
    // Intersects left or right edge
    t = hw / absDx;
  } else {
    // Intersects top or bottom edge
    t = hh / absDy;
  }

  return {
    x: center.x + dx * t,
    y: center.y + dy * t,
  };
}

/**
 * Get anchor points for a circular node
 */
export function getCircularBorderPoint(
  center: Point,
  radius: number,
  targetCenter: Point
): Point {
  const dx = targetCenter.x - center.x;
  const dy = targetCenter.y - center.y;
  const dist = Math.sqrt(dx * dx + dy * dy);

  if (dist === 0) {
    return { x: center.x + radius, y: center.y };
  }

  return {
    x: center.x + (dx / dist) * radius,
    y: center.y + (dy / dist) * radius,
  };
}

/**
 * Generate a smooth bezier curve path between two points
 */
export function getBezierPath(
  start: Point,
  end: Point,
  options: {
    curvature?: number;
  } = {}
): string {
  const { curvature = 0.25 } = options;

  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dist = Math.sqrt(dx * dx + dy * dy);

  // Calculate control points for a smooth curve
  // Control points perpendicular to the line
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;

  // Simple quadratic bezier with control point at midpoint, offset perpendicularly
  const controlX = midX - dy * curvature;
  const controlY = midY + dx * curvature;

  return `M ${start.x} ${start.y} Q ${controlX} ${controlY} ${end.x} ${end.y}`;
}

/**
 * Generate a straight line path with arrow marker
 */
export function getLinePath(start: Point, end: Point): string {
  return `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
}

/**
 * Calculate arrow head points
 */
export function getArrowHead(
  end: Point,
  start: Point,
  size: number = 10
): Point[] {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dist = Math.sqrt(dx * dx + dy * dy);

  if (dist === 0) {
    return [
      { x: end.x, y: end.y },
      { x: end.x - size, y: end.y - size / 2 },
      { x: end.x - size, y: end.y + size / 2 },
    ];
  }

  // Unit vector in direction of line
  const ux = dx / dist;
  const uy = dy / dist;

  // Perpendicular vector
  const px = -uy;
  const py = ux;

  // Arrow points
  const tip = end;
  const left = {
    x: end.x - size * ux + size * 0.4 * px,
    y: end.y - size * uy + size * 0.4 * py,
  };
  const right = {
    x: end.x - size * ux - size * 0.4 * px,
    y: end.y - size * uy - size * 0.4 * py,
  };

  return [tip, left, right];
}

/**
 * Convert points array to SVG path string for polygon
 */
export function pointsToPath(points: Point[]): string {
  if (points.length === 0) return '';

  return points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
    .join(' ') + ' Z';
}

/**
 * Calculate edge path between two nodes
 */
export function calculateEdgePath(
  fromNode: NodeBounds,
  toNode: NodeBounds,
  options: {
    isCircular?: {
      from: boolean;
      to: boolean;
    };
    fromRadius?: number;
    toRadius?: number;
    curved?: boolean;
  } = {}
): { path: string; arrowPoints: Point[] } {
  const fromCenter = getNodeCenter(fromNode);
  const toCenter = getNodeCenter(toNode);

  let startPoint: Point;
  let endPoint: Point;

  if (options.isCircular?.from && options.fromRadius) {
    startPoint = getCircularBorderPoint(fromCenter, options.fromRadius, toCenter);
  } else {
    startPoint = getBorderPoint(fromNode, toCenter);
  }

  if (options.isCircular?.to && options.toRadius) {
    // Offset end point slightly before the edge for arrow
    const offset = 12;
    const dx = toCenter.x - fromCenter.x;
    const dy = toCenter.y - fromCenter.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    const rawEnd = getCircularBorderPoint(toCenter, options.toRadius, fromCenter);
    if (dist > 0) {
      endPoint = {
        x: rawEnd.x + (dx / dist) * offset,
        y: rawEnd.y + (dy / dist) * offset,
      };
    } else {
      endPoint = rawEnd;
    }
  } else {
    // Offset for arrow
    const dx = toCenter.x - fromCenter.x;
    const dy = toCenter.y - fromCenter.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    const rawEnd = getBorderPoint(toNode, fromCenter);
    if (dist > 0) {
      const offset = 5;
      endPoint = {
        x: rawEnd.x + (dx / dist) * offset,
        y: rawEnd.y + (dy / dist) * offset,
      };
    } else {
      endPoint = rawEnd;
    }
  }

  const path = options.curved
    ? getBezierPath(startPoint, endPoint)
    : getLinePath(startPoint, endPoint);

  const arrowPoints = getArrowHead(endPoint, startPoint, 10);

  return { path, arrowPoints };
}
