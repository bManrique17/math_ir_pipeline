const BASE_URL = "/api";

export async function fetchPosts(offset, limit) {
  const res = await fetch(`${BASE_URL}/posts?offset=${offset}&limit=${limit}`);
  if (!res.ok) {
    throw new Error(`Failed to load posts (${res.status})`);
  }
  return res.json();
}

export async function fetchPostBySilverId(silverId) {
  const res = await fetch(`${BASE_URL}/posts/${silverId}`);
  if (res.status === 404) {
    throw new Error(`No post found with silver_id ${silverId}`);
  }
  if (!res.ok) {
    throw new Error(`Failed to load post (${res.status})`);
  }
  return res.json();
}

export async function fetchFormulaGraph(id) {
  const res = await fetch(`${BASE_URL}/formulas/${id}/graph`);
  if (res.status === 404) {
    throw new Error(`No formula found with id ${id}`);
  }
  if (!res.ok) {
    throw new Error(`Failed to load formula graph (${res.status})`);
  }
  return res.json();
}

export async function fetchFormulas(offset, limit) {
  const res = await fetch(`${BASE_URL}/formulas?offset=${offset}&limit=${limit}`);
  if (!res.ok) {
    throw new Error(`Failed to load formulas (${res.status})`);
  }
  return res.json();
}

export async function fetchFormulaById(id) {
  const res = await fetch(`${BASE_URL}/formulas/${id}`);
  if (res.status === 404) {
    throw new Error(`No formula found with id ${id}`);
  }
  if (!res.ok) {
    throw new Error(`Failed to load formula (${res.status})`);
  }
  return res.json();
}
