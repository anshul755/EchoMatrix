# Anshul Prompt Log

This is the AI-assistance log I kept while building EchoMatrix. I did use AI heavily for scaffolding and for speeding up repetitive implementation, but most of the useful work came from reviewing outputs, testing them against the actual dataset, and then correcting the places where the first pass was too generic or too fragile.

I am listing the prompts in the rough order they were used. For each one, I included the component, the prompt itself, and a short note on what went wrong and what I changed after the output.

## 1. Dataset schema inference

- Component: backend data understanding
- Prompt: "Read `backend/data/data.jsonl`, infer the true schema instead of guessing, identify which fields are reliable, and propose a canonical internal post model for search, topics, trends, and network analysis."
- What was wrong and how I fixed it: the first answer treated the dataset like a mixed social media corpus; I rechecked the full file and rewrote the schema around the fact that it is a Reddit submissions dataset only.

## 2. Dataset documentation

- Component: dataset notes
- Prompt: "Write a concise schema note describing the raw JSONL format, required fields, optional fields, derived fields, and what should be ignored."
- What was wrong and how I fixed it: the first draft was too abstract and read like documentation for an imaginary dataset, so I rewrote it around the actual fields present in the JSONL and saved that as `backend/DATA_SCHEMA.md`.

## 3. Loader implementation

- Component: backend data loader
- Prompt: "Build a FastAPI-friendly JSONL loader that reads line by line, skips malformed rows safely, normalizes the Reddit records, preserves raw payloads, and returns a DataFrame-compatible structure for the rest of the app."
- What was wrong and how I fixed it: the first output only handled happy-path rows; I added malformed row handling, raw payload preservation, canonical fields, and a repository-style wrapper.

## 4. Loader caching

- Component: backend performance
- Prompt: "Add caching so the normalized dataset does not have to be rebuilt on every startup, but make sure cache invalidation depends on the source file."
- What was wrong and how I fixed it: the initial version cached too aggressively; I tied cache validity to file signature and added a reload path.

## 5. Semantic search baseline

- Component: search backend
- Prompt: "Implement semantic search over the normalized post text using sentence embeddings, cosine similarity, snippets, and relevance-ranked results."
- What was wrong and how I fixed it: the first pass had the right structure but weak metadata and no graceful empty-query behavior, so I added better response models, snippets, and input validation.

## 6. Search fallback behavior

- Component: search reliability
- Prompt: "Add a fallback path so semantic search still works when sentence-transformers is unavailable or the filtered corpus is very small."
- What was wrong and how I fixed it: the first fallback was too naive and could produce inconsistent shapes; I added TF-IDF fallback and a small/sparse token-overlap path.

## 7. Search metadata and UI contract

- Component: search API contract
- Prompt: "Return richer fields for every result: snippet, author, timestamp, URL, score, subreddit, domain, comment count, media type, and anything else useful for a dashboard detail view."
- What was wrong and how I fixed it: some returned values were not normalized cleanly and could include empty or NaN-like data, so I cleaned metadata before serialization.

## 8. Related query suggestions

- Component: search product polish
- Prompt: "After returning search results, suggest two or three related follow-up queries that a user might explore next."
- What was wrong and how I fixed it: the first version depended too much on the model always being available, so I added a simple data-derived fallback when GenAI suggestions are unavailable.

## 9. Time-series aggregation

- Component: trends backend
- Prompt: "Create a time-series endpoint that buckets matching posts by hour, day, or week and supports grouping by platform, author, hashtag, and topic."
- What was wrong and how I fixed it: the first implementation worked for normal queries but not for stress cases, so I tightened filtering and empty/sparse handling.

## 10. Dynamic plain-language summaries

- Component: AI summaries
- Prompt: "Generate a plain-language summary beneath each trend chart using the actual returned time-series data, not hardcoded text."
- What was wrong and how I fixed it: the first output sounded generic; I rebuilt the summary flow around structured bucket data and added a rule-based fallback derived from the real counts.

## 11. Topic clustering first pass

- Component: topics backend
- Prompt: "Cluster posts into themes with embeddings plus KMeans, produce readable labels, representative posts, and cluster-level metadata."
- What was wrong and how I fixed it: the labels and representatives were too noisy on repetitive data, so I changed the post selection logic and added stronger cluster guardrails.

## 12. Extreme cluster-count handling

- Component: topics robustness
- Prompt: "Make the topics endpoint safe for extreme `n_clusters` values and small datasets."
- What was wrong and how I fixed it: the first route-level validation could reject oversized values before the service had a chance to reduce them, so I moved the safety behavior into the service flow and removed the overly strict route cap.

## 13. Embedding visualization export

- Component: topics visualization
- Prompt: "Expose the topic-model embeddings in a format that can be opened in TensorFlow Projector and linked from the dashboard."
- What was wrong and how I fixed it: the first version only exported vectors; I added aligned metadata, a manifest, and large-dataset export limits so the visualization stayed usable.

## 14. Network analysis design

- Component: network backend
- Prompt: "Build network analysis for this dataset, including centrality scoring, community detection, and support for testing graph resilience by removing an influential node."
- What was wrong and how I fixed it: the first idea assumed reply or mention relationships that do not exist in this dataset, so I rebuilt the graph logic around inferred relationships such as shared hashtags, URLs, authors, topic labels, and activity patterns.

## 15. Network edge cases

- Component: network robustness
- Prompt: "Handle disconnected components, sparse graphs, malformed URLs, and missing relationship types without crashing."
- What was wrong and how I fixed it: malformed URLs and sparse filtered graphs exposed brittle assumptions, so I added safe parsing, explicit graph metadata, and graceful empty/sparse responses.

## 16. Frontend shell

- Component: React app structure
- Prompt: "Create a serious investigative dashboard shell in React with a sidebar, topbar, reusable cards, and routes for dashboard, search, trends, topics, network, and about."
- What was wrong and how I fixed it: the first frontend layout felt too generic, so I restyled it into a more project-specific investigative interface and replaced placeholder sections with dataset-driven content.

## 17. Search page UI

- Component: search frontend
- Prompt: "Build a semantic search page with a search box, ranked results, detail drawer, loading/empty/error states, and suggested follow-up queries."
- What was wrong and how I fixed it: the early version still behaved too much like keyword search, and later I also had to fix a real bug where URL syncing interfered with typing spaces into the search field.

## 18. Trends page UI

- Component: trends frontend
- Prompt: "Create a trends page that tells a story with the chart, summary, filters, grouped view, and event overlays."
- What was wrong and how I fixed it: the first layout was visually fine but too chart-only, so I added summary context, facts, event comparison, and more resilient empty/sparse states.

## 19. Topics page UI

- Component: topics frontend
- Prompt: "Create a topic clustering page with a cluster count control, cluster cards, metadata, representative posts, and an embedding visualization area."
- What was wrong and how I fixed it: the first page covered the basics but missed some backend response details, so I added parameter notes, error states, and projector export actions.

## 20. Network page UI

- Component: network frontend
- Prompt: "Build an interactive network page in React using a graph library, with filters, node details, community display, and resilience output."
- What was wrong and how I fixed it: the first page did not fully reflect the backend’s inferred-relationship metadata, so I updated the controls and detail panels to match the real API.

## 21. Landing page redesign

- Component: frontend landing page
- Prompt: "Replace the plain landing page with a more polished homepage using OGL Aurora, cleaner branding, and project-specific copy."
- What was wrong and how I fixed it: the early version looked too much like a generated template, so I removed fake-looking brand elements, folded the about content into the landing flow, and retuned spacing and section boundaries by hand.

## 22. Dashboard overview API

- Component: backend dashboard performance
- Prompt: "Create one fast cached backend overview endpoint so the dashboard does not depend on many expensive requests on first load."
- What was wrong and how I fixed it: the first dashboard approach depended on several separate endpoints and felt slow, so I added `GET /api/dashboard/overview` with in-memory caching and a lighter payload.

## 23. Dashboard layout and story

- Component: dashboard frontend
- Prompt: "Redesign the dashboard overview to feel like an investigative command center, using project-related charts and summaries instead of generic admin widgets."
- What was wrong and how I fixed it: the first version had repeated information and awkward empty areas, so I replaced duplicate cards, added more useful charts, and adjusted the grid until it fit the page better.

## 24. Offline event overlay

- Component: nice-to-have feature
- Prompt: "Add a lightweight offline event format and use it to overlay real-world events on the trends page with before/after comparison."
- What was wrong and how I fixed it: the initial version only attached events loosely; I added a backend loader, an events endpoint, and a clearer frontend comparison panel.

## 25. Robustness audit

- Component: cross-cutting review
- Prompt: "Audit the whole system for stress-test failures: malformed data, empty results, short queries, regex-like input, disconnected graphs, cluster extremes, and broken UI states."
- What was wrong and how I fixed it: this surfaced several real issues, including literal query handling in filters, malformed URL crashes, cache mismatches, and frontend empty-state gaps, which I then fixed and documented in `backend/ROBUSTNESS_AUDIT.md`.

## 26 Documentation cleanup

- Component: submission docs
- Prompt: "Write a README that explains the architecture, dataset, API shapes, ML choices, robustness decisions, and remaining gaps honestly."
- What was wrong and how I fixed it: the first README draft was accurate but still too generic in some places, so I revised it to match the actual endpoints, Gemini usage, and the final project structure.

## Final note

I did not accept AI output blindly. The recurring pattern throughout this project was:

- use AI to speed up a first pass
- compare the result against the real dataset and real UI behavior
- test edge cases
- rewrite the parts that were too generic, too fragile, or too polished-looking

The places where this mattered most were dataset normalization, search fallback behavior, stress-case handling, dashboard performance, and aligning the frontend with the real backend response contracts.
