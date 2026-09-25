import { Link } from "react-router-dom";

import { useMathJaxTypeset } from "../hooks/useMathJax";

function buildRows(formulas, descriptors) {
  const byId = new Map((formulas || []).map((f) => [f.id, f]));
  const descriptorIds = Object.keys(descriptors || {}).map(Number);
  const ids = new Set([...byId.keys(), ...descriptorIds]);
  return [...ids]
    .sort((a, b) => a - b)
    .map((id) => ({
      id,
      latex: byId.get(id)?.latex ?? null,
      descriptions: (descriptors || {})[String(id)] || [],
    }));
}

export default function FormulaTable({ formulas, descriptors }) {
  const rows = buildRows(formulas, descriptors);
  const ref = useMathJaxTypeset([rows]);

  if (rows.length === 0) {
    return <p className="text-muted fst-italic">No formulas</p>;
  }

  return (
    <table ref={ref} className="table table-sm table-bordered align-middle">
      <thead>
        <tr>
          <th>ID</th>
          <th>Formula</th>
          <th>Descriptions</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>{row.id}</td>
            <td>
              {row.latex ? `\\(${row.latex}\\)` : <span className="text-muted fst-italic">(no latex)</span>}
            </td>
            <td>
              {row.descriptions.length > 0 ? (
                <ul className="mb-0 ps-3">
                  {row.descriptions.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              ) : (
                <span className="text-muted fst-italic">none</span>
              )}
            </td>
            <td>
              <Link to={`/formula/${row.id}`} className="link-secondary small">
                View graph
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
