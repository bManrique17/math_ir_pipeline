import { useState } from "react";

export default function SearchBar({
  onSearch,
  onClear,
  searchActive,
  placeholder = "Search by silver_id",
  clearLabel = "Check full list again",
}) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim() === "") return;
    onSearch(value.trim());
  };

  return (
    <form className="d-flex align-items-center gap-2" onSubmit={handleSubmit}>
      <input
        type="number"
        className="form-control"
        style={{ maxWidth: "240px" }}
        placeholder={placeholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit" className="btn btn-primary">
        Search
      </button>
      {searchActive && (
        <button type="button" className="btn btn-outline-secondary" onClick={onClear}>
          {clearLabel}
        </button>
      )}
    </form>
  );
}
