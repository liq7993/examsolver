import type { SolveDiagramPrimitive } from "./solveBackendTypes";
import type { DiagramBlockViewModel } from "./solveWorkbenchViewModel";
import styles from "./SolveWorkbench.module.css";

function polarPoint(centerX: number, centerY: number, radius: number, angleDeg: number) {
  const radians = (angleDeg * Math.PI) / 180;
  return {
    x: centerX + radius * Math.cos(radians),
    y: centerY - radius * Math.sin(radians),
  };
}

function forceArrowColor(primitive: Extract<SolveDiagramPrimitive, { kind: "force_arrow" }>): string {
  switch (primitive.role) {
    case "balancing":
      return "#0f766e";
    case "component_x":
      return "#2563eb";
    case "component_y":
      return "#dc2626";
    case "resultant":
      return "#7c3aed";
    default:
      return "#1f2933";
  }
}

function estimateLabelWidth(text: string) {
  return Array.from(text).reduce((width, char) => {
    if (/[\u4e00-\u9fff]/.test(char)) {
      return width + 13;
    }

    return width + 7;
  }, 14);
}

function labelColor(tone: "default" | "muted" | "accent") {
  if (tone === "accent") {
    return "#0f766e";
  }

  if (tone === "muted") {
    return "#64748b";
  }

  return "#1f2933";
}

function renderTextLabel(input: {
  id: string;
  x: number;
  y: number;
  text: string;
  color: string;
  opacity: number;
  fontSize?: number;
}) {
  const fontSize = input.fontSize ?? 13;
  const width = Math.max(30, estimateLabelWidth(input.text));

  return (
    <g key={input.id} opacity={input.opacity}>
      <rect
        x={input.x - 7}
        y={input.y - fontSize - 5}
        width={width}
        height={fontSize + 10}
        rx={6}
        fill="rgba(255,255,255,0.88)"
        stroke="rgba(148,163,184,0.28)"
      />
      <text
        x={input.x}
        y={input.y}
        fontSize={fontSize}
        fill={input.color}
        fontFamily="var(--font-ui), sans-serif"
      >
        {input.text}
      </text>
    </g>
  );
}

function renderPrimitive(
  primitive: SolveDiagramPrimitive,
  activePrimitiveIds: Set<string>,
  options?: { showArrowLabels?: boolean },
) {
  const isActive = activePrimitiveIds.size === 0 || activePrimitiveIds.has(primitive.id);
  const opacity = isActive ? 1 : 0.22;

  switch (primitive.kind) {
    case "body":
      return (
        <rect
          key={primitive.id}
          x={primitive.x}
          y={primitive.y}
          width={primitive.width}
          height={primitive.height}
          rx={18}
          fill="#f8fafc"
          stroke="#cbd5e1"
          strokeWidth={2}
          opacity={opacity}
        />
      );
    case "highlight_box":
      return (
        <rect
          key={primitive.id}
          x={primitive.x}
          y={primitive.y}
          width={primitive.width}
          height={primitive.height}
          rx={14}
          fill={primitive.tone === "result" ? "rgba(20,184,166,0.12)" : "rgba(37,99,235,0.1)"}
          stroke={primitive.tone === "result" ? "#14b8a6" : "#2563eb"}
          strokeWidth={2}
          strokeDasharray="8 6"
          opacity={opacity}
        />
      );
    case "axis":
      return (
        <g key={primitive.id} opacity={opacity}>
          <line
            x1={primitive.origin.x}
            y1={primitive.origin.y}
            x2={primitive.origin.x + primitive.x_length}
            y2={primitive.origin.y}
            stroke="#94a3b8"
            strokeWidth={2}
          />
          <line
            x1={primitive.origin.x}
            y1={primitive.origin.y}
            x2={primitive.origin.x}
            y2={primitive.origin.y - primitive.y_length}
            stroke="#94a3b8"
            strokeWidth={2}
          />
          <text x={primitive.origin.x + primitive.x_length + 8} y={primitive.origin.y + 4} fontSize="14" fill="#64748b">
            x
          </text>
          <text x={primitive.origin.x - 12} y={primitive.origin.y - primitive.y_length - 8} fontSize="14" fill="#64748b">
            y
          </text>
        </g>
      );
    case "force_arrow":
      return (
        <g key={primitive.id} opacity={opacity}>
          <line
            x1={primitive.from.x}
            y1={primitive.from.y}
            x2={primitive.to.x}
            y2={primitive.to.y}
            stroke={forceArrowColor(primitive)}
            strokeWidth={3.2}
            strokeLinecap="round"
            markerEnd={`url(#arrow-${primitive.role})`}
          />
          {options?.showArrowLabels === true
            ? renderTextLabel({
                id: `${primitive.id}_arrow_label`,
                x: primitive.to.x + 8,
                y: primitive.to.y - 8,
                text: primitive.label,
                color: forceArrowColor(primitive),
                opacity: 1,
                fontSize: 13,
              })
            : null}
        </g>
      );
    case "label":
      return renderTextLabel({
        id: primitive.id,
        x: primitive.position.x,
        y: primitive.position.y,
        text: primitive.text,
        color: labelColor(primitive.tone),
        opacity,
      });
    case "angle_marker": {
      const start = polarPoint(primitive.center.x, primitive.center.y, primitive.radius, primitive.start_deg);
      const end = polarPoint(primitive.center.x, primitive.center.y, primitive.radius, primitive.end_deg);
      const largeArcFlag = Math.abs(primitive.end_deg - primitive.start_deg) > 180 ? 1 : 0;
      const sweepFlag = primitive.end_deg >= primitive.start_deg ? 0 : 1;
      return (
        <path
          key={primitive.id}
          d={`M ${start.x} ${start.y} A ${primitive.radius} ${primitive.radius} 0 ${largeArcFlag} ${sweepFlag} ${end.x} ${end.y}`}
          fill="none"
          stroke="#64748b"
          strokeWidth={2}
          opacity={opacity}
        />
      );
    }
    default:
      return null;
  }
}

export function SolveDiagramCanvas({
  block,
  activeStepId,
}: {
  block: DiagramBlockViewModel | null;
  activeStepId: string | null;
}) {
  if (!block || block.primitives.length === 0) {
    return (
      <div className={styles.emptyDiagram}>
        <p>{block?.emptyMessage ?? "当前题目还没有可展示的 v0 图解。"}</p>
      </div>
    );
  }

  const activePrimitiveIds = new Set(
    activeStepId
      ? block.steps.find((step) => step.id === activeStepId)?.primitive_ids ?? []
      : [],
  );

  return (
    <svg
      viewBox={`0 0 ${block.viewport.width} ${block.viewport.height}`}
      className={styles.diagramSvg}
      aria-label="解题图解"
    >
      <defs>
        <marker id="arrow-given" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0 0 L8 4 L0 8 Z" fill="#1f2933" />
        </marker>
        <marker id="arrow-balancing" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0 0 L8 4 L0 8 Z" fill="#0f766e" />
        </marker>
        <marker id="arrow-component_x" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0 0 L8 4 L0 8 Z" fill="#2563eb" />
        </marker>
        <marker id="arrow-component_y" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0 0 L8 4 L0 8 Z" fill="#dc2626" />
        </marker>
        <marker id="arrow-resultant" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0 0 L8 4 L0 8 Z" fill="#7c3aed" />
        </marker>
      </defs>
      <rect x="0" y="0" width={block.viewport.width} height={block.viewport.height} fill="#ffffff" />
      {block.primitives
        .filter((primitive) => primitive.kind !== "label")
        .map((primitive) => renderPrimitive(primitive, activePrimitiveIds))}
      {block.primitives
        .filter((primitive) => primitive.kind === "label")
        .map((primitive) => renderPrimitive(primitive, activePrimitiveIds))}
    </svg>
  );
}
