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

export async function fetchVocabById(id) {
  const res = await fetch(`${BASE_URL}/vocab/${id}`);
  if (res.status === 404) {
    throw new Error(`No vocab found with id ${id}`);
  }
  if (!res.ok) {
    throw new Error(`Failed to load vocab (${res.status})`);
  }
  return res.json();
}

export async function fetchRetrieval(latex, topK) {
  const params = new URLSearchParams({ latex, top_k: topK });
  const res = await fetch(`${BASE_URL}/retrieval?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to retrieve formulas (${res.status})`);
  }
  return res.json();
}

export async function fetchGoldFormulaGraph(id) {
  const res = await fetch(`${BASE_URL}/gold_formulas/${id}/graph`);
  if (res.status === 404) {
    throw new Error(`No gold formula found with id ${id}`);
  }
  if (!res.ok) {
    throw new Error(`Failed to load formula graph (${res.status})`);
  }
  return res.json();
}

export async function fetchMultimodalRetrieval(query, topK) {
  const params = new URLSearchParams({ query, top_k: topK });
  const res = await fetch(`${BASE_URL}/multimodal_retrieval?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to retrieve posts (${res.status})`);
  }
  return res.json();
}

export async function fetchSilverFormulaGraph(id) {
  const res = await fetch(`${BASE_URL}/silver_formulas/${id}/graph`);
  if (res.status === 404) {
    throw new Error(`No silver formula found with silver_id ${id}`);
  }
  if (!res.ok) {
    throw new Error(`Failed to load formula graph (${res.status})`);
  }
  return res.json();
}

export async function fetchAnnotatedRetrieval(query, topK) {
  const params = new URLSearchParams({ query, top_k: topK });
  const res = await fetch(`${BASE_URL}/annotated_retrieval?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to retrieve formulas (${res.status})`);
  }
  return res.json();
}

export async function fetchMultimodalRetrievalAnnotated(query, topK) {
  const params = new URLSearchParams({ query, top_k: topK });
  const res = await fetch(`${BASE_URL}/multimodal_retrieval_annotated?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to retrieve posts (${res.status})`);
  }
  return res.json();
}

// ---- ARQMath Task 1 evaluation (proxied to the retrieval service's /task1 API) ----

async function task1Get(path, params) {
  const res = await fetch(`${BASE_URL}/task1/${path}?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : body?.detail ? JSON.stringify(body.detail) : null;
    throw new Error(detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export function fetchTask1Topics(arqmathVersion) {
  return task1Get("topics", new URLSearchParams({ arqmath_version: arqmathVersion }));
}

// topicIds: optional array; empty/undefined = all evaluated topics. Blocking, can take ~30 min.
export function fetchTask1Evaluation({ arqmathVersion, retriever, topK, topicIds }) {
  const params = new URLSearchParams({ arqmath_version: arqmathVersion, retriever, top_k: topK });
  for (const id of topicIds ?? []) params.append("topic_ids", id);
  return task1Get("evaluate", params);
}

export function fetchTask1TopicResults(topicId, { arqmathVersion, retriever, topK, judgedOnly = false, offset = 0, limit = 1000 }) {
  const params = new URLSearchParams({
    arqmath_version: arqmathVersion,
    retriever,
    top_k: topK,
    judged_only: judgedOnly,
    offset,
    limit,
  });
  return task1Get(`topics/${encodeURIComponent(topicId)}/results`, params);
}
