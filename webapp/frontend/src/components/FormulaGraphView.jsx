import { useEffect, useRef } from "react";
import svgPanZoom from "svg-pan-zoom";

// The SVG markup itself (nodes, edges, labels, colors) is rendered server-side
// via graphviz (see webapp/backend/app/render.py) -- this component only wires
// up pan/zoom on whatever <svg> comes back, same library/config DEBUG/viz_opt.py
// already used via CDN for its modal graph viewer.
export default function FormulaGraphView({ title, graph }) {
  const containerRef = useRef(null);
  const panZoomRef = useRef(null);

  useEffect(() => {
    if (panZoomRef.current) {
      panZoomRef.current.destroy();
      panZoomRef.current = null;
    }
    const svgEl = containerRef.current?.querySelector("svg");
    if (!svgEl) return;

    svgEl.setAttribute("width", "100%");
    svgEl.setAttribute("height", "100%");
    panZoomRef.current = svgPanZoom(svgEl, {
      zoomEnabled: true,
      controlIconsEnabled: true,
      fit: true,
      center: true,
      minZoom: 0.05,
      maxZoom: 20,
      mouseWheelZoomEnabled: true,
      dblClickZoomEnabled: true,
    });

    return () => {
      panZoomRef.current?.destroy();
      panZoomRef.current = null;
    };
  }, [graph]);

  if (!graph?.available) {
    return (
      <div>
        <h6 className="text-uppercase text-muted small">{title}</h6>
        <p className="text-muted fst-italic">No {title} graph available for this formula.</p>
      </div>
    );
  }

  return (
    <div>
      <h6 className="text-uppercase text-muted small d-flex align-items-center gap-2">
        {title}
        {graph.annotated && <span className="badge text-bg-warning">annotated</span>}
      </h6>
      <div
        ref={containerRef}
        style={{ height: 480, border: "1px solid #e1e0d9", borderRadius: 6, overflow: "hidden" }}
        // eslint-disable-next-line react/no-danger -- SVG is rendered server-side by our own graphviz call
        dangerouslySetInnerHTML={{ __html: graph.svg }}
      />
    </div>
  );
}
