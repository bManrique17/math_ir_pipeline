import { useCallback, useEffect, useRef, useState } from "react";

import { fetchPostBySilverId, fetchPosts } from "./api";
import PostRow from "./components/PostRow";
import SearchBar from "./components/SearchBar";

const PAGE_SIZE = 10;

export default function App() {
  const [posts, setPosts] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchActive, setSearchActive] = useState(false);
  const initialized = useRef(false);

  const loadPage = useCallback(async (currentOffset) => {
    setLoading(true);
    setError(null);
    try {
      const { items, has_more } = await fetchPosts(currentOffset, PAGE_SIZE);
      setPosts((prev) => [...prev, ...items]);
      setOffset(currentOffset + PAGE_SIZE);
      setHasMore(has_more);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    loadPage(0);
  }, [loadPage]);

  const handleSearch = async (silverId) => {
    setLoading(true);
    setError(null);
    try {
      const post = await fetchPostBySilverId(silverId);
      setPosts([post]);
      setSearchActive(true);
      setHasMore(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClearSearch = () => {
    setError(null);
    setPosts([]);
    setOffset(0);
    setHasMore(true);
    setSearchActive(false);
    loadPage(0);
  };

  return (
    <div className="container py-4">
      <h1 className="mb-4">Formula descriptor</h1>
      <SearchBar onSearch={handleSearch} onClear={handleClearSearch} searchActive={searchActive} />

      {error && <div className="alert alert-danger">{error}</div>}

      {posts.map((post) => (
        <PostRow key={post.silver_id} post={post} />
      ))}

      {!searchActive && (
        <div className="text-center my-4">
          {hasMore ? (
            <button
              className="btn btn-outline-primary"
              disabled={loading}
              onClick={() => loadPage(offset)}
            >
              {loading ? "Loading..." : "Show more"}
            </button>
          ) : (
            posts.length > 0 && <p className="text-muted">No more posts</p>
          )}
        </div>
      )}
    </div>
  );
}
