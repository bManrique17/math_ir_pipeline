import { useMathJaxTypeset } from "../hooks/useMathJax";

export default function FormulaTable({ formulas }) {
  const ref = useMathJaxTypeset([formulas]);

  if (!formulas || formulas.length === 0) {
    return <p className="text-muted fst-italic">No formulas</p>;
  }

  return (
    <table ref={ref} className="table table-sm table-bordered align-middle">
      <thead>
        <tr>
          <th>ID</th>
          <th>Formula</th>
        </tr>
      </thead>
      <tbody>
        {formulas.map((f) => (
          <tr key={f.id}>
            <td>{f.id}</td>
            <td>{`\\(${f.latex}\\)`}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
