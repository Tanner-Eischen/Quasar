# Week 3 Frontend Implementation Plan
## 2D Konva Proto-Star Graph (Days 17-22)

---

## Day 17: Setup + File Nodes (8 hours)

### **Task 1: React Project Setup** (1 hour)

```bash
cd C:/Users/tanne/Gauntlet/LegacyLens/ui
mkdir graph
cd graph

# Initialize project
npm init -y

# Install dependencies
npm install react react-dom react-konva konva zustand
npm install -D vite @vitejs/plugin-react typescript @types/react @types/react-dom

# Create vite.config.ts
cat > vite.config.ts << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
EOF

# Create tsconfig.json
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF
```

**Directory structure:**
```
ui/graph/
├── src/
│   ├── components/
│   │   ├── GraphCanvas.tsx         # Main canvas (from BoardCanvas)
│   │   ├── FileNodeObject.tsx      # File proto-stars (from ClusterNodeObject)
│   │   ├── SymbolNodeObject.tsx    # Subroutine rectangles (new, simple)
│   │   └── CallEdgeObject.tsx      # Golden edges (from ConnectorObject)
│   ├── utils/
│   │   ├── symbol-layout.ts        # Layout algorithms (from cluster-layout)
│   │   └── graph-store.ts          # Zustand state (from board-store)
│   ├── styles/
│   │   └── graph.css               # Cosmic theme (from globals.css)
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

### **Task 2: Copy CollabCanvas Base Components** (2 hours)

**From CollabCanvas, copy and adapt:**

1. **BoardCanvas.tsx → GraphCanvas.tsx**
   - Remove: Drawing tools, game object creation
   - Keep: Zoom, pan, viewport management, selection
   - Add: Graph-specific controls

2. **globals.css → graph.css**
   - Keep: Cosmic starfield background, proto-star styles, golden glow
   - Remove: Game-specific styles
   - Add: Graph legend styles

3. **board-store.ts → graph-store.ts**
   - Adapt: Objects → Nodes, Connections → Edges
   - Keep: Selection, viewport state

### **Task 3: Fetch and Display File Nodes** (3 hours)

**Create: `src/components/FileNodeObject.tsx`**

Based on `ClusterNodeObject.tsx` but simplified for MVP:

```typescript
import { Circle, Group, Text } from 'react-konva';
import { useState } from 'react';

interface FileNodeProps {
  id: string;
  name: string;
  x: number;
  y: number;
  symbolCount: number;
  onClick: (id: string) => void;
  onDragEnd: (id: string, x: number, y: number) => void;
}

export const FileNodeObject = ({
  id, name, x, y, symbolCount, onClick, onDragEnd
}: FileNodeProps) => {
  const [isDragging, setIsDragging] = useState(false);
  
  // Proto-star appearance
  const radius = 34;
  const glowColor = '#FFD700'; // Gold
  
  return (
    <Group
      x={x}
      y={y}
      draggable
      onDragStart={() => setIsDragging(true)}
      onDragEnd={(e) => {
        setIsDragging(false);
        onDragEnd(id, e.target.x(), e.target.y());
      }}
      onClick={() => onClick(id)}
      onTap={() => onClick(id)}
    >
      {/* Outer glow */}
      <Circle
        radius={radius + 10}
        fill={glowColor}
        opacity={0.2}
        blur={20}
      />
      
      {/* Proto-star body */}
      <Circle
        radius={radius}
        fill={glowColor}
        strokeWidth={2}
        stroke="#FFF"
        shadowBlur={isDragging ? 30 : 15}
        shadowColor={glowColor}
        shadowOpacity={0.8}
      />
      
      {/* Symbol count badge */}
      <Circle
        x={radius * 0.7}
        y={-radius * 0.7}
        radius={12}
        fill="#1a1a2e"
        stroke={glowColor}
        strokeWidth={1}
      />
      <Text
        x={radius * 0.7 - 6}
        y={-radius * 0.7 - 6}
        text={symbolCount.toString()}
        fontSize={12}
        fill="#FFF"
        fontStyle="bold"
      />
      
      {/* File name label */}
      <Text
        y={radius + 10}
        text={name}
        fontSize={14}
        fill="#FFF"
        align="center"
        offsetX={name.length * 3.5} // Approximate centering
      />
    </Group>
  );
};
```

**Create: `src/utils/graph-store.ts`**

```typescript
import { create } from 'zustand';

interface FileNode {
  id: string;
  type: 'file';
  name: string;
  path: string;
  x: number;
  y: number;
  symbolCount: number;
  expanded: boolean;
}

interface SymbolNode {
  id: string;
  type: 'symbol';
  name: string;
  kind: string;
  fileId: string;
  line: number;
  x: number;
  y: number;
}

interface Edge {
  id: string;
  from: string;
  to: string;
  type: 'symbol-to-symbol' | 'file-to-symbol';
  kind: string;
  line: number;
  snippet: string;
}

interface GraphState {
  nodes: (FileNode | SymbolNode)[];
  edges: Edge[];
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchGraph: (corpusId: number) => Promise<void>;
  updateNodePosition: (id: string, x: number, y: number) => void;
  toggleFileExpanded: (id: string) => void;
}

export const useGraphStore = create<GraphState>((set, get) => ({
  nodes: [],
  edges: [],
  loading: false,
  error: null,
  
  fetchGraph: async (corpusId: number) => {
    set({ loading: true, error: null });
    
    try {
      const response = await fetch(`/api/v1/graph/${corpusId}`);
      if (!response.ok) throw new Error('Failed to fetch graph');
      
      const data = await response.json();
      
      // Transform API response to store format
      const nodes = data.nodes.map((node: any) => ({
        ...node,
        expanded: false, // All files start collapsed
      }));
      
      set({
        nodes,
        edges: data.edges,
        loading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Unknown error',
        loading: false,
      });
    }
  },
  
  updateNodePosition: (id: string, x: number, y: number) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id ? { ...node, x, y } : node
      ),
    }));
  },
  
  toggleFileExpanded: (id: string) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === id && node.type === 'file'
          ? { ...node, expanded: !node.expanded }
          : node
      ),
    }));
  },
}));
```

**Create: `src/App.tsx`**

```typescript
import { useEffect } from 'react';
import { GraphCanvas } from './components/GraphCanvas';
import { useGraphStore } from './utils/graph-store';
import './styles/graph.css';

function App() {
  const { fetchGraph, loading, error } = useGraphStore();
  
  useEffect(() => {
    fetchGraph(1); // Load corpus ID 1
  }, [fetchGraph]);
  
  if (loading) {
    return <div className="loading">Loading graph...</div>;
  }
  
  if (error) {
    return <div className="error">Error: {error}</div>;
  }
  
  return (
    <div className="app">
      <GraphCanvas />
    </div>
  );
}

export default App;
```

### **Task 4: Test File Nodes Rendering** (2 hours)

```bash
npm run dev
# Open http://localhost:5173
```

**Expected result:**
- 27 file nodes rendered as golden proto-stars in circular arrangement
- Each shows symbol count badge
- Draggable
- Click shows alert (placeholder for expand)

---

## Day 18: Symbol Expansion + Grid Layout (6 hours)

### **Task 1: Copy Symbol Layout Algorithm** (1 hour)

**From CollabCanvas: `cluster-layout.ts` → `symbol-layout.ts`**

```typescript
export interface LayoutConfig {
  containerWidth: number;
  containerHeight: number;
  padding: number;
  symbolWidth: number;
  symbolHeight: number;
}

export function gridLayout(
  symbolCount: number,
  config: LayoutConfig
): Array<{ x: number; y: number }> {
  const { containerWidth, containerHeight, padding, symbolWidth, symbolHeight } = config;
  
  // Calculate grid dimensions
  const cols = Math.ceil(Math.sqrt(symbolCount));
  const rows = Math.ceil(symbolCount / cols);
  
  const cellWidth = (containerWidth - padding * 2) / cols;
  const cellHeight = (containerHeight - padding * 2) / rows;
  
  const positions = [];
  for (let i = 0; i < symbolCount; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    
    positions.push({
      x: padding + col * cellWidth + symbolWidth / 2,
      y: padding + row * cellHeight + symbolHeight / 2,
    });
  }
  
  return positions;
}
```

### **Task 2: Implement File Expansion** (3 hours)

**Update: `src/components/FileNodeObject.tsx`**

Add expanded state rendering:

```typescript
// Inside FileNodeObject component
const { nodes, toggleFileExpanded } = useGraphStore();

// Find symbols belonging to this file
const fileSymbols = nodes.filter(
  node => node.type === 'symbol' && node.fileId === id
);

const expanded = /* get from props or store */;

if (expanded) {
  // Render expanded nebula container
  const containerWidth = 400;
  const containerHeight = 300;
  
  return (
    <Group x={x} y={y}>
      {/* Nebula container background */}
      <Rect
        x={-containerWidth / 2}
        y={-containerHeight / 2}
        width={containerWidth}
        height={containerHeight}
        fill="rgba(26, 26, 46, 0.9)"
        stroke="#FFD700"
        strokeWidth={2}
        cornerRadius={10}
        shadowBlur={30}
        shadowColor="#FFD700"
      />
      
      {/* Header with file name */}
      <Text
        x={-containerWidth / 2 + 10}
        y={-containerHeight / 2 + 10}
        text={name}
        fontSize={16}
        fill="#FFF"
        fontStyle="bold"
      />
      
      {/* Symbol count badge */}
      <Text
        x={containerWidth / 2 - 40}
        y={-containerHeight / 2 + 10}
        text={`[${symbolCount}]`}
        fontSize={14}
        fill="#FFD700"
      />
      
      {/* Render symbols in grid */}
      {fileSymbols.map((symbol, idx) => (
        <SymbolNodeObject
          key={symbol.id}
          {...symbol}
          localX={symbolPositions[idx].x - containerWidth / 2}
          localY={symbolPositions[idx].y - containerHeight / 2}
        />
      ))}
    </Group>
  );
}

// Otherwise render collapsed proto-star (existing code)
```

### **Task 3: Create Symbol Node Component** (2 hours)

**Create: `src/components/SymbolNodeObject.tsx`**

```typescript
import { Rect, Group, Text } from 'react-konva';

interface SymbolNodeProps {
  id: string;
  name: string;
  kind: string;
  localX: number;  // Position relative to parent container
  localY: number;
  onClick: (id: string) => void;
}

export const SymbolNodeObject = ({
  id, name, kind, localX, localY, onClick
}: SymbolNodeProps) => {
  const width = 120;
  const height = 40;
  
  return (
    <Group
      x={localX}
      y={localY}
      onClick={() => onClick(id)}
      onTap={() => onClick(id)}
    >
      {/* Symbol rectangle */}
      <Rect
        x={-width / 2}
        y={-height / 2}
        width={width}
        height={height}
        fill="#4169E1"
        stroke="#6495ED"
        strokeWidth={1}
        cornerRadius={5}
        shadowBlur={5}
        shadowColor="#4169E1"
        shadowOpacity={0.5}
      />
      
      {/* Symbol name */}
      <Text
        y={-6}
        text={name}
        fontSize={12}
        fill="#FFF"
        align="center"
        width={width}
        offsetX={width / 2}
      />
    </Group>
  );
};
```

**Test:** Double-click file → expands to show subroutines in grid

---

## Day 19: Edges + RAG Integration (6 hours)

### **Task 1: Implement Call Edges** (3 hours)

**Create: `src/components/CallEdgeObject.tsx`**

Based on CollabCanvas `ConnectorObject.tsx`:

```typescript
import { Line, Arrow } from 'react-konva';

interface CallEdgeProps {
  from: { x: number; y: number };
  to: { x: number; y: number };
  type: 'symbol-to-symbol' | 'file-to-symbol';
  snippet: string;
}

export const CallEdgeObject = ({ from, to, type, snippet }: CallEdgeProps) => {
  const strokeWidth = type === 'file-to-symbol' ? 2 : 1;
  const color = '#FFD700'; // Golden thread
  
  return (
    <Arrow
      points={[from.x, from.y, to.x, to.y]}
      stroke={color}
      strokeWidth={strokeWidth}
      fill={color}
      pointerLength={8}
      pointerWidth={8}
      opacity={0.6}
      shadowBlur={5}
      shadowColor={color}
      // Future 2.5D: This will need 3D bezier curves
    />
  );
};
```

**Update: `src/components/GraphCanvas.tsx`**

Render edges behind nodes:

```typescript
<Layer name="edges">
  {edges.map(edge => {
    const fromNode = findNode(edge.from);
    const toNode = findNode(edge.to);
    
    if (!fromNode || !toNode) return null;
    
    return (
      <CallEdgeObject
        key={edge.id}
        from={{ x: fromNode.x, y: fromNode.y }}
        to={{ x: toNode.x, y: toNode.y }}
        type={edge.type}
        snippet={edge.snippet}
      />
    );
  })}
</Layer>

<Layer name="nodes">
  {/* Render file and symbol nodes */}
</Layer>
```

### **Task 2: Source Code Panel** (2 hours)

**Create: `src/components/SourceCodePanel.tsx`**

```typescript
import { useState, useEffect } from 'react';

interface SourceCodePanelProps {
  symbolId: string | null;
  onClose: () => void;
}

export const SourceCodePanel = ({ symbolId, onClose }: SourceCodePanelProps) => {
  const [code, setCode] = useState<string>('');
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (!symbolId) return;
    
    setLoading(true);
    fetch(`/api/v1/symbols/${symbolId}`)
      .then(res => res.json())
      .then(data => {
        setCode(data.source || 'No source available');
        setLoading(false);
      });
  }, [symbolId]);
  
  if (!symbolId) return null;
  
  return (
    <div className="source-panel">
      <div className="source-header">
        <h3>Source Code</h3>
        <button onClick={onClose}>×</button>
      </div>
      <div className="source-body">
        {loading ? (
          <div>Loading...</div>
        ) : (
          <pre><code>{code}</code></pre>
        )}
      </div>
    </div>
  );
};
```

### **Task 3: Link to RAG Search** (1 hour)

Add button to source panel:

```typescript
<button onClick={() => {
  // Navigate to search with pre-filled query
  window.location.href = `/search?q=Tell me about ${symbolName}`;
}}>
  Ask Claude about this symbol
</button>
```

---

## Day 20-21: Polish & Animations (10 hours)

### **Cosmic Theme Polish** (4 hours)

**Create: `src/styles/graph.css`**

```css
/* Starfield background */
.app {
  background: radial-gradient(ellipse at bottom, #1B2735 0%, #090A0F 100%);
  min-height: 100vh;
  overflow: hidden;
  position: relative;
}

/* Animated stars */
.app::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: 
    radial-gradient(2px 2px at 20px 30px, #eee, transparent),
    radial-gradient(2px 2px at 60px 70px, #fff, transparent),
    radial-gradient(1px 1px at 50px 50px, #ddd, transparent),
    radial-gradient(1px 1px at 130px 80px, #fff, transparent),
    radial-gradient(2px 2px at 90px 10px, #eee, transparent);
  background-size: 200px 200px;
  animation: twinkle 3s infinite;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

/* Proto-star glow animation */
@keyframes protostar-pulse {
  0%, 100% {
    filter: drop-shadow(0 0 15px #FFD700);
  }
  50% {
    filter: drop-shadow(0 0 25px #FFD700);
  }
}
```

### **Expand/Collapse Animation** (3 hours)

Use `react-konva` Tween for smooth transitions:

```typescript
import { Tween, Easings } from 'konva/lib/Tween';

// When expanding
const tween = new Tween({
  node: groupRef.current,
  duration: 0.4,
  scaleX: 1.5,
  scaleY: 1.5,
  easing: Easings.EaseOut,
});
tween.play();
```

### **Edge Routing** (2 hours)

Implement bezier curves for edges:

```typescript
// Calculate control points for smooth curves
const controlX = (from.x + to.x) / 2;
const controlY = Math.min(from.y, to.y) - 50;

<Line
  points={[
    from.x, from.y,
    controlX, controlY,
    to.x, to.y
  ]}
  bezier
  stroke="#FFD700"
/>
```

### **Legend + Minimap** (1 hour)

Add UI overlays for legend and minimap placeholders.

---

## Day 22: Demo Video (4 hours)

### **Script:**

1. **Opening** (30s): Show collapsed proto-star galaxy
2. **Navigation** (45s): Zoom, pan, drag files
3. **Expansion** (60s): Double-click → grid of subroutines
4. **Edges** (45s): Golden CALL threads between nodes
5. **Source** (30s): Click symbol → show code
6. **Closing** (30s): "Week 3 complete, 2.5D coming in Week 4"

---

## Week 4: Upgrade to 2.5D (Optional Enhancement)

After Week 3 2D deployment, enhance to 2.5D:

### **Changes Required:**

1. **Add Z-coordinate to nodes:**
   - Files: `z: 0`
   - Symbols: `z: 100`

2. **Apply isometric transform to stage:**
   ```javascript
   stage.scaleY(0.866); // cos(30°)
   stage.skewX(-30);
   ```

3. **Update edges to 3D lines:**
   - Calculate Z-offset for vertical separation
   - Add depth cues (thinner lines when farther)

4. **Add depth effects:**
   - Shadows from symbols onto file layer
   - Parallax scrolling
   - Atmospheric fade for distant nodes

**Estimated time:** 6-8 hours on top of 2D base

---

## Summary Timeline

| Day | Focus | Hours | Deliverable |
|-----|-------|-------|-------------|
| 16 | Graph API | 6-8 | Backend endpoint |
| 17 | React + File nodes | 8 | Proto-stars render |
| 18 | Symbol expansion | 6 | Expand/collapse works |
| 19 | Edges + RAG link | 6 | Full graph + integration |
| 20-21 | Polish | 10 | Animations + theme |
| 22 | Demo | 4 | Video ready |
| **Total** | | **40-42** | **2D deployed** |
| Week 4 | 2.5D upgrade | 6-8 | Depth layers |

This approach:
✅ Ships working 2D by end of Week 3
✅ Maximizes CollabCanvas reuse (70%)
✅ Provides upgrade path to 2.5D
✅ De-risks the timeline
