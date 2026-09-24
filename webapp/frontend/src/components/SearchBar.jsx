import { useState } from "react";

export default function SearchBar({ onSearch, onClear, searchActive }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim() === "") return;
    onSearch(value.trim());
  };

  return (
    <form className="d-flex align-items-center gap-2 mb-4" onSubmit={handleSubmit}>
      <input
        type="number"
        className="form-control"
        style={{ maxWidth: "240px" }}
        placeholder="Search by silver_id"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit" className="btn btn-primary">
        Search
      </button>
      {searchActive && (
        <button type="button" className="btn btn-outline-secondary" onClick={onClear}>
          Check full list again
        </button>
      )}
    </form>
  );
}
