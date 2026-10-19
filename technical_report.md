# Technical report — Research & Expertise Navigator, Saarlanders

- **Challenge:** Bern Economic Development Agency: Research & Expertise Navigator
- **Event:** On-site Liebefeld
- **Team:** Saarlanders — Jayasankar Kumar Santhirani, Deivanai Shankar, Amina Aneefa, Jesmilan Jesu
- **Demo:** `link to video`

## 1. Summary

Research expertise in Bern is described across many institutional websites, in vocabulary that often differs from the vocabulary of the person searching. The system indexes 64 configured hosts (University of Bern (UniBE) including the ARTORG Center for Biomedical Engineering Research, Diabetes Center Berne (DCB), Inselspital clinics, and several support and regulatory sites) into 538 research units (institutes, labs, research groups) and 5,002 person records. Agency staff paste or upload (PDF) a company's business model; Apertus v1.5 8B [1] drafts a list of needs (the need card), which staff edit; the search returns up to ten leads, units proposed for those needs, with people, expertise terms, projects and facilities, and verbatim source sentences with their URLs, each checked against the live page at search time. Apertus v1.5 70B writes the unit summaries at build time, and a second 70B call checks each summary sentence against the source text. On 12 test queries with 34 expected people, labs and projects, 31 of 34 appear in the top 10 (10 of 12 on the four queries kept out of tuning); with the same queries rephrased in other terms, 26 of 34.

| Success criterion | Result |
| --- | --- |
| 1. Right people in the top 10 (target ≥ 80%) | 91% (31/34); queries kept out of tuning 83% (10/12) |
| 2. Different wording finds the same experts | 76% (26/34) with rephrased queries; below the 80% target |
| 3. Every result traceable | 0 links outside the fetched dataset; every generated sentence checked against its sources; quotes re-checked on the live page |
| 4. Structured results | person, function, affiliation, unit, expertise, projects, facilities and services, reason, source link, where the source has them |
| 5. UniBE, ARTORG and DCB covered | share of queries with a top-10 lead from each: 100% / 58% / 50% |
| 6. Easy to extend | one config line per site; a new site type is a template block, not code |

## 2. Architecture

The system consists of an offline build (`navigator` command line), Postgres 16 with pgvector, a stateless FastAPI service and a React front end, run with Docker Compose.

```text
BUILD (offline)                                           REQUEST (api, stateless)
config/domains/medtech.yaml (64 hosts, 9 templates)       business model (text or PDF -> Docling/EasyOCR)
  fetch     robots.txt, 1 req/s/host, WordPress API,        needs        Apertus 8B draft, edited by staff
            headless Chromium for JavaScript sites          per need:
  extract   content area, units, people, projects             expand     Apertus 8B, terms en/de/fr
  enrich    Apertus 70B summary + terms + category            retrieve   full-text en/de/fr + vector, fused
  support   Apertus 70B checks each summary sentence          rerank     bge-reranker-v2-m3
  embed     BGE-M3 chunks (<=350 words) + term chunks       select       greedy coverage, 10 units
  load      fresh staging schema, 11 checks                 lead         quotes, people, projects, terms
  go live   schema rename in one transaction                explain      Apertus 8B, checked by 70B
            \______ Postgres + pgvector ______/             live check   quoted pages fetched again
```

**Build.** Hosts are crawled from configured start pages at one request per second, following robots.txt [2] (including wildcard rules). DCB is read through its WordPress API; sitem-insel.ch, which renders with JavaScript, through headless Chromium. Per-template CSS selectors define the content area; e-mail addresses and phone numbers are removed from the text. A unit is a host or a URL path matched by a configured pattern. People come from schema.org `Person` markup or configured person-card selectors; heads, directors, leaders and principal investigators are marked as contact persons. For each unit, Apertus 70B receives up to 60 numbered sentences and returns a two-sentence summary, terms in English, German and French, and a category; each summary sentence is then checked as described in section 3. Pages are split into chunks of at most 350 words and embedded with BGE-M3 [3], plus one chunk per unit and language holding its terms. A build is loaded into a staging schema and goes live only if 11 checks pass (among them: every URL fetched with HTTP 200, no contact data in served text, no page with text addressed to an AI system). Model answers and embeddings are cached by input hash, so a rebuild processes only changed pages.

**Request.** Apertus 8B expands each need into search terms in three languages. Postgres full-text search and pgvector search (top 200 each) are fused by reciprocal rank [4], with a small bonus for shared MeSH (Medical Subject Headings) concepts, and bge-reranker-v2-m3 [5] rescores the top chunks. A greedy step picks ten units that together cover the needs, penalising near-duplicate units; among units of nearly equal gain the one with fewer pages is chosen. Each lead quotes, for each need it matches, the best sentence of its best chunk with URL and page date. Apertus 8B writes a one-sentence explanation from those quotes; it is shown only if the 70B check confirms it. In parallel, each quoted page is fetched again and the quote is marked `found`, `changed`, `gone` or `unreachable` (pages that need JavaScript are marked `not checked`). A coverage line names needs without a lead above a score threshold. The search streams each step to the front end as it happens (search terms, sites searched, leads picked, checks). Staff can download the result as a PDF report, which adds sections on Bern as a location (clinical studies, regulatory route) written at build time from listed pages.

**Adding a site.** A site using an existing template takes one host line in `config/domains/medtech.yaml`; a new site type takes a template block (selectors, start pages, person cards), not code.

### Target architecture

The system is designed for **(a) on-premise** and **(c) sovereign Swiss cloud** deployment, and can run **(b) air-gapped** with the steps below. All models have open weights. Apertus is reached through an OpenAI-compatible URL; during the hackathon this was the event gateway, and a self-hosted vLLM server [6] can replace it without code changes. In bf16, the 70B weights need about 140 GB of GPU memory, the 8B weights about 16 GB.

| | Build time | Runtime |
| --- | --- | --- |
| External network | the 64 hosts; model weights (Hugging Face); packages and images | Apertus endpoint; institutional hosts (live check) |
| Local models | BGE-M3, reranker | BGE-M3, reranker, Docling [7], EasyOCR |

For (b), the index is built on a connected machine and imported (`navigator snapshot export/import`), the model weights are copied, and the live check, which needs outside access, is left out (this needs a configuration switch, which is not yet implemented).

## 3. Use of Apertus

Apertus v1.5 8B and 70B (non-thinking) are used for inference only, through a vLLM-based OpenAI-compatible endpoint. No fine-tuning and no tool use.

| Task | Model | Phase | Temp. |
| --- | --- | --- | --- |
| Unit summary, terms en/de/fr, category | 70B | build | 0.2 |
| Support check of summary, report and explanation sentences | 70B | build, request | 0.0 |
| Location sections of the PDF report, each sentence citing its page | 70B | build | 0.2 |
| Need card from a business model | 8B | request | 0.2 |
| Need expansion into search terms | 8B | request | 0.0 |
| One-sentence explanation per lead | 8B | request | 0.0 |

**Output format.** Every call uses constrained decoding with a JSON schema (vLLM `structured_outputs`). In an unconstrained trial, 292 of 400 summary answers had the wrong structure. Every answer is validated with pydantic: cited sentence numbers must exist, summaries may not contain markup or contact data, categories come from a fixed list. A failing answer stops the build; there are no retries.

**Support check.** For each generated sentence, a separate 70B call reads the numbered source sentences and returns the numbers of those that support it. A sentence without support is removed, and the supporting sentences become its sources. The writer cites too few sentences on its own, so the check, not the writer's citations, determines the sources.

**Model choice.** In early runs the 8B writer added uncited details and the 8B checker rejected a correct summary. Build tasks therefore use 70B, request-time tasks 8B for latency.

**Untrusted input.** Crawled pages and company documents may contain instructions aimed at the model. Apertus has no tools or secrets, and its output is validated JSON. Outside text is sent as numbered lines in a `<quoted>` block that the system prompt marks as data; angle brackets in it are replaced so it cannot close the block. Text addressed to an AI system ("ignore previous instructions", `SYSTEM:` and similar patterns) stops the build when found in a page and is removed from a business model before drafting, with the removed sentence shown to staff. Text extracted from a PDF, including text hidden in it, is shown to staff before drafting. The front end and PDF renderer output escaped text only. On a test set of 10 pages and 5 business models with planted instructions, all 10 pages are flagged and none of the 5 drafted need cards follows the instruction.

## 4. Data

| Source | Access |
| --- | --- |
| University of Bern (49 unibe.ch hosts: the supplied inventory plus hosts the team checked and added) | crawl, shared portal template |
| ARTORG (`artorg.unibe.ch`) | crawl; research groups by URL path |
| Diabetes Center Berne | WordPress REST API; modelled by focus area, not by lab |
| Inselspital (7 clinic hosts) and Insel Gruppe; Bern University of Applied Sciences (BFH); sitem-insel (translational medicine); be-advanced (start-up support); Swissmedic (regulator); Innosuisse (innovation agency); Switzerland Innovation Park Biel/Bienne | crawl; 7 further site templates |

The build used here contains 10,282 pages, 538 units, 861 projects and facilities, 5,002 person records and 23,242 chunks. Excluded: hosts that were unreachable, used an unsupported layout or a self-signed certificate, and Swiss Medtech, whose robots.txt reserves rights against AI training and is silent on use as model input, pending the agency's decision. Vocabulary: 443 MeSH concepts [8] with English, German and French labels (MeSH, NLM; German MeSH, ZB MED, CC BY 4.0; Wikidata, CC0).

**Licence and personal data.** Only public pages are used. Page text stays under the institutions' copyright and is not in the repository. Person records (name, function, affiliation, e-mail, phone) are personal data under the nDSG and GDPR [9] although published; contact data is removed from page text before any model sees it and is stored only in the person table. The service is intended for agency staff and should be deployed on a network only they can reach, since the API has no login of its own.

## 5. Evaluation

The team wrote 12 test queries (for example "glucose sensors", "artificial pancreas", "lung on a chip") and listed 34 expected entries: people, labs and projects a good answer should contain, each mapped by hand to its unit. Recall@10 is the share of expected entries whose unit is among the top ten leads; as several entries can share a unit, it is also given per distinct query–unit pair (21 pairs). Eight queries were used for tuning. Four were held out: "gut bacteria and obesity", "cochlear implant surgery", "tumour detection during surgery with light" and "clinical trial support for a medtech start-up"; two entries of the last one, CTU Bern and sitem-insel, were mapped to their units once their sites were added to the index. For the wording test, the team rephrased each query in the terms a specialist or layperson might use instead (for example "glucose sensors" as "CGM, continuous glucose monitoring, biosensing, wearable sensing, metabolic monitoring"). `navigator eval` runs the same ranking function as the API.

| Measure | Result |
| --- | --- |
| Recall@10, all 12 queries (entries; query–unit pairs) | 31/34; 18/21 |
| Recall@10, 4 held-out queries (entries; query–unit pairs) | 10/12; 6/8 |
| Recall@10 with rephrased queries (entries; all 12; 4 held-out) | 26/34; 8/12 |
| Overlap of the top ten for original and rephrased query (units in both / units in either, mean) | 0.42 |
| Queries with a top-10 lead from UniBE / ARTORG / DCB | 100% / 58% / 50% |
| Top-10 places held by small units (≤ 5 pages, which are 75% of all units) | 33% |
| Lead and quote links that were not fetched with HTTP 200 | 0 |
| Quotes still on the live page at search time (one two-need search) | 9/9 |

Misses with the original wording: for "artificial pancreas", ARTORG's AI in Health and Nutrition lab; for "clinical trial support for a medtech start-up", the Department of Clinical Research (two of its sub-units appear instead of the department itself) and the ARTORG Center. For comparison, Google site search found 16 of 122 expected entries in its top 10 (13%), measured by the team on its first answer key of 15 queries, counted per person and item.

Latency on a laptop with the local models on its GPU: about 3 s per need for retrieval and reranking; 12–16 s for a two-need search including people, explanations and the live check.

## 6. Limitations

- **Evaluation size:** 12 queries written by the team; a larger set with relevance judgements from agency staff is the next step.
- **Granularity:** results are ranked by unit; people are attached to their unit, with contact persons identified from their function.
- **Explanations:** an explanation is shown only when the 70B check confirms it, so some leads show quotes without one; on the test queries, their rephrasings and 8 business models, 161 of 202 explanations (80%) were confirmed.
- **Extraction:** each site type needs a template of CSS selectors, which must be updated when a site changes its layout.

## 7. Reproducibility

Any machine with Docker Compose and 16 GB of memory runs the system: the API image is built on `python:3.11-slim` with CPU PyTorch and headless Chromium, the database is `pgvector/pgvector:pg16`. The local models (BGE-M3, reranker, Docling, EasyOCR) run on the CPU by default (`TORCH_DEVICE=cpu`); outside Docker they can use an NVIDIA (`cuda`) or Apple (`mps`) GPU. Apertus runs wherever the endpoint points; it is set with the template's `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_NAME` (the 8B model) in `src/.env`, plus `LLM_NAME_LARGE` for the 70B model, since both are used. The numbers in this report come from commit `09da943`. No random seeds are set: model answers and embeddings are cached by input hash, so restoring the team's built index and caches (`make restore`, a 275 MB Postgres dump published as release `index-v1`) reproduces them exactly, while a fresh crawl (`make index`, several hours) reflects the sites on the day it runs.

```bash
cd src
cp .env.example .env              # set DB_PASSWORD (also in DATABASE_URL) and LLM_API_KEY
make restore                      # download the built index (release index-v1) and load it into Postgres
make up                           # db, api (port 8000), web (http://localhost:$WEB_PORT); first start downloads the local models
make eval DOMAIN=medtech SPLIT=all
# instead of make restore, build the index from the live sites (several hours):
make up && make index DOMAIN=medtech
```

## License

Apache License 2.0 (see `LICENSE`). All HackApertus projects are open-sourced.

## References

1. Swiss AI Initiative. Apertus v1.5 8B and 70B. https://huggingface.co/swiss-ai/Apertus-v1.5-8B, https://huggingface.co/swiss-ai/Apertus-v1.5-70B
2. Koster, M. et al. (2022). RFC 9309: Robots Exclusion Protocol. IETF.
3. Chen, J. et al. (2024). BGE M3-Embedding. arXiv:2402.03216.
4. Cormack, G. V., Clarke, C. L. A., Büttcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. SIGIR 2009.
5. BAAI. bge-reranker-v2-m3. https://huggingface.co/BAAI/bge-reranker-v2-m3
6. Kwon, W. et al. (2023). Efficient Memory Management for Large Language Model Serving with PagedAttention (vLLM). SOSP 2023.
7. Auer, C. et al. (2024). Docling Technical Report. arXiv:2408.09869.
8. U.S. National Library of Medicine, MeSH; ZB MED, German MeSH; Wikidata.
9. Federal Act on Data Protection (nDSG), SR 235.1; Regulation (EU) 2016/679 (GDPR).
