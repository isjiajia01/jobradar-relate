# Similar jobs by lexical and graph evidence

Run `make similar JOB=j06` from the repository root. The first run installs the pinned `relate-db==1.2.0` dependency if needed. Retrieval runs locally without a model or API key. Each invocation copies the synthetic `jobradar.rl` bundle into a temporary directory, opens that copy, writes job vectors, and creates a Relate cosine vector index. The temporary directory is removed when the command exits.

## Reading the results

The embedding is a toy lexical bag of words. Each occurrence of a case-folded word from the title, description (when present), and required skill names increments one of 256 counters. The synthetic jobs have titles and skills only. The bucket is the first four SHA-256 bytes of the UTF-8 token, interpreted as a big-endian integer modulo 256. Word order is lost, synonyms can be missed, and unrelated tokens can collide. This measures token overlap and has no semantic model.

`db.index.vector.queryNodes` searches the index. Relate 1.2.0 uses an exact scan. For this ten-job fixture we request every indexed job, exclude the query job, sort by descending similarity and then ascending job ID, and keep three. Relate reports rebounded cosine, where 0.5 means orthogonal and 1 means identical direction.

Within these three, a direct `SIMILAR_TO` edge comes first, then a shared company, then lexical rank. The printed edge value is its stored weight. `my verdict` shows the synthetic user’s direct `LIKED` or `DISMISSED` edge on that candidate as context. A dismissed job can still be the closest match. The default recommendation scorer runs independently.

## Vector-only pair check

`make similar-check` queries each endpoint of the two specified fixture pairs before graph reranking. The shortlist size is the same three used for display.

| Query and expected neighbor | Lexical rank |
| --- | ---: |
| j01 → j02 | 1 |
| j02 → j01 | 1 |
| j05 → j06 | 1 |
| j06 → j05 | 1 |

Both pairs surfaced in both directions (4/4 at k=3). Each pair shares its exact title and two required skills. The importer uses title and skill overlap to create these links, so this small check measures agreement on synthetic fixtures and cannot establish real-world retrieval quality. Rebuilding and scanning the full index on each invocation is suitable for this demo size.
