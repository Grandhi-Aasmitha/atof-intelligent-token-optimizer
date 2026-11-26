---
name: ATOF context retrieval
description: Prefer optimized source retrieval for targeted code explanations and dependency questions.
---
For a targeted question about an identified source file, prefer the ATOF optimized source tool (#atofContext) before requesting full file contents. Pass the actual task and workspace-relative path, never raw source in arguments. Only authorized files. If unavailable, disabled or insufficient, use normal authorized tools. For edits or exact full-file reviews, read required original source. Do not claim provider token savings or native prompt rewriting. Do not call for unrelated questions.
