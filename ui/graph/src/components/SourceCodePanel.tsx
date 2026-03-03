import React, { useEffect, useState, useCallback } from 'react';
import { useGraphStore, selectSymbolById } from '../utils/graph-store';

interface SourceResponse {
  symbol: {
    id: number;
    name: string;
    kind: string;
    span: {
      file_path: string;
      start_line: number;
      end_line: number;
    };
    signature: string | null;
  };
  explanation: string | null;
}

interface SourceLine {
  number: number;
  content: string;
}

export const SourceCodePanel: React.FC = () => {
  const {
    sourcePanelOpen,
    sourceSymbolId,
    closeSourcePanel,
  } = useGraphStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceData, setSourceData] = useState<SourceResponse | null>(null);
  const [sourceLines, setSourceLines] = useState<SourceLine[]>([]);

  // Get symbol from store
  const symbol = useGraphStore((state) =>
    sourceSymbolId ? selectSymbolById(state, sourceSymbolId) : null
  );

  // Fetch source code when symbol changes
  useEffect(() => {
    if (!sourceSymbolId || !sourcePanelOpen) {
      setSourceData(null);
      setSourceLines([]);
      return;
    }

    const fetchSource = async () => {
      setLoading(true);
      setError(null);

      try {
        // Extract symbol name from node ID (format: "symbol-123")
        const symbolName = symbol?.name;
        if (!symbolName) {
          throw new Error('Symbol not found');
        }

        const response = await fetch(`/api/v1/symbols/${encodeURIComponent(symbolName)}`);

        if (!response.ok) {
          throw new Error(`Failed to fetch source: ${response.statusText}`);
        }

        const data: SourceResponse = await response.json();
        setSourceData(data);

        // Fetch actual source code from file
        if (data.symbol.span) {
          const fileResponse = await fetch(
            `/api/v1/files/${data.symbol.span.file_path}/content`
          );

          if (fileResponse.ok) {
            const fileContent = await fileResponse.text();
            const lines = fileContent.split('\n');
            const startLine = Math.max(0, data.symbol.span.start_line - 5);
            const endLine = Math.min(lines.length, data.symbol.span.end_line + 5);

            const sourceLines: SourceLine[] = [];
            for (let i = startLine; i < endLine; i++) {
              sourceLines.push({
                number: i + 1,
                content: highlightFortran(lines[i] || ''),
              });
            }

            setSourceLines(sourceLines);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load source');
      } finally {
        setLoading(false);
      }
    };

    fetchSource();
  }, [sourceSymbolId, sourcePanelOpen, symbol]);

  const handleClose = useCallback(() => {
    closeSourcePanel();
  }, [closeSourcePanel]);

  if (!sourcePanelOpen) {
    return null;
  }

  return (
    <div className={`source-panel ${sourcePanelOpen ? 'open' : ''}`}>
      <div className="source-panel-header">
        <div className="source-panel-title">
          {symbol ? symbol.name : 'Source Code'}
        </div>
        <button className="source-panel-close" onClick={handleClose}>
          ×
        </button>
      </div>

      {loading && (
        <div style={{ padding: '20px', textAlign: 'center', color: '#8B949E' }}>
          Loading source...
        </div>
      )}

      {error && (
        <div style={{ padding: '20px', color: '#F85149' }}>
          {error}
        </div>
      )}

      {sourceData && (
        <>
          {/* Symbol info */}
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid rgba(255, 193, 7, 0.1)',
            background: 'rgba(255, 193, 7, 0.05)',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '8px',
            }}>
              <span style={{
                background: '#4169E1',
                color: 'white',
                padding: '2px 8px',
                borderRadius: '3px',
                fontSize: '10px',
                fontWeight: '600',
              }}>
                {sourceData.symbol.kind}
              </span>
              <span style={{ color: '#8B949E', fontSize: '11px' }}>
                {sourceData.symbol.span.file_path}:{sourceData.symbol.span.start_line}
              </span>
            </div>

            {sourceData.explanation && (
              <div style={{
                color: '#C9D1D9',
                fontSize: '12px',
                lineHeight: '1.5',
              }}>
                {sourceData.explanation}
              </div>
            )}
          </div>

          {/* Source code */}
          <div className="source-code">
            {sourceLines.map((line) => (
              <div
                key={line.number}
                className="source-line"
                style={{
                  background:
                    sourceData.symbol.span.start_line <= line.number &&
                    line.number <= sourceData.symbol.span.end_line
                      ? 'rgba(255, 193, 7, 0.1)'
                      : 'transparent',
                }}
              >
                <span className="line-number">{line.number}</span>
                <span
                  className="line-content"
                  dangerouslySetInnerHTML={{ __html: line.content }}
                />
              </div>
            ))}
          </div>

          {/* Ask Claude button */}
          <div style={{
            padding: '16px',
            borderTop: '1px solid rgba(255, 193, 7, 0.1)',
          }}>
            <a
              href={`/?query=Explain the ${sourceData.symbol.kind} ${symbol?.name}`}
              style={{
                display: 'block',
                width: '100%',
                padding: '10px 16px',
                background: 'linear-gradient(135deg, #FFC107 0%, #FF9800 100%)',
                color: '#000000',
                textAlign: 'center',
                borderRadius: '6px',
                textDecoration: 'none',
                fontWeight: '600',
                fontSize: '12px',
              }}
            >
              Ask Claude about this symbol
            </a>
          </div>
        </>
      )}
    </div>
  );
};

/**
 * Simple Fortran syntax highlighting
 */
function highlightFortran(line: string): string {
  // Escape HTML first
  let highlighted = line
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Fortran keywords
  const keywords = [
    'SUBROUTINE', 'FUNCTION', 'PROGRAM', 'MODULE', 'END',
    'CALL', 'RETURN', 'STOP', 'PAUSE', 'GOTO', 'CONTINUE',
    'IF', 'THEN', 'ELSE', 'ENDIF', 'DO', 'ENDDO', 'WHILE',
    'INTEGER', 'REAL', 'DOUBLE', 'COMPLEX', 'LOGICAL', 'CHARACTER',
    'DIMENSION', 'PARAMETER', 'COMMON', 'EQUIVALENCE', 'EXTERNAL',
    'IMPLICIT', 'NONE', 'SAVE', 'DATA', 'FORMAT', 'WRITE', 'READ',
    'OPEN', 'CLOSE', 'ALLOCATE', 'DEALLOCATE', 'NULLIFY',
    'USE', 'INCLUDE', 'ONLY', 'PRIVATE', 'PUBLIC', 'INTENT',
    'IN', 'OUT', 'INOUT', 'OPTIONAL', 'RECURSIVE', 'PURE',
  ];

  // Comments (lines starting with ! or c)
  if (/^\s*[!cC]/.test(highlighted)) {
    return `<span class="comment">${highlighted}</span>`;
  }

  // String literals
  highlighted = highlighted.replace(/'[^']*'/g, '<span class="string">$&</span>');
  highlighted = highlighted.replace(/"[^"]*"/g, '<span class="string">$&</span>');

  // Numbers
  highlighted = highlighted.replace(/\b\d+\.?\d*([dDeE][+-]?\d+)?\b/g, '<span class="number">$&</span>');

  // Keywords (case-insensitive)
  for (const keyword of keywords) {
    const regex = new RegExp(`\\b(${keyword}|${keyword.toLowerCase()})\\b`, 'g');
    highlighted = highlighted.replace(regex, '<span class="keyword">$1</span>');
  }

  return highlighted;
}

export default SourceCodePanel;
