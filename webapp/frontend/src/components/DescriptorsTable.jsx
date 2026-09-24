export default function DescriptorsTable({ descriptors }) {
  const entries = Object.entries(descriptors || {});

  if (entries.length === 0) {
    return <p className="text-muted fst-italic">No descriptors</p>;
  }

  return (
    <table className="table table-sm table-bordered align-middle">
      <thead>
        <tr>
          <th>ID</th>
          <th>Descriptions</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([id, descs]) => (
          <tr key={id}>
            <td>{id}</td>
            <td>
              <ul className="mb-0 ps-3">
                {descs.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
