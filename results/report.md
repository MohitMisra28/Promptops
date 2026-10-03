# PromptOps comparison report

50 fixed test cases. Mock backends: latency is **simulated**, cost uses **hypothetical** price tables (small $0.0002/$0.0006, large $0.003/$0.015 per 1k tokens in/out).

| config | schema valid (first try) | schema valid (final) | instruction following | pass rate | mean latency s | p95 s | tokens | cost USD | retry | fallback |
|---|---|---|---|---|---|---|---|---|---|---|
| v1 + mock-small | 59% | 96% | 75% | 76% | 0.757 | 1.36 | 6791 | 0.00287 | 16% | 0% |
| v1 + mock-large | 94% | 98% | 77% | 78% | 2.056 | 2.784 | 5967 | 0.05865 | 4% | 0% |
| v2 + mock-small | 84% | 96% | 98% | 98% | 0.681 | 0.928 | 12709 | 0.00392 | 4% | 0% |
| v2 + mock-large | 94% | 98% | 100% | 100% | 2.063 | 2.784 | 12874 | 0.0797 | 4% | 0% |
| v2 + router (fallback on) | 86% | 98% | 100% | 100% | 1.092 | 2.484 | 12927 | 0.02764 | 4% | 2% |

## Is the cheaper model enough? (prompt v2, no fallback)

| task | small pass | large pass | small cost | large cost | verdict |
|---|---|---|---|---|---|
| announcement | 100% | 100% | 0.00076 | 0.01478 | small model is enough |
| content_pack | 100% | 100% | 0.00114 | 0.02377 | small model is enough |
| schedule | 93% | 100% | 0.00122 | 0.02563 | small model is NOT enough |
| task_list | 100% | 100% | 0.0008 | 0.01552 | small model is enough |

## Failures by config

**v1 + mock-small** - 12 failing case(s)
- `tc04` (content_pack): expected exactly 4 hashtags, got 3
- `tc08` (content_pack): expected exactly 4 hashtags, got 3
- `tc12` (content_pack): expected exactly 4 hashtags, got 3
- `tc16` (content_pack): expected exactly 4 hashtags, got 3
- `tc20` (content_pack): expected exactly 4 hashtags, got 3
- `tc24` (content_pack): expected exactly 4 hashtags, got 3
- `tc28` (content_pack): expected exactly 4 hashtags, got 3
- `tc32` (content_pack): expected exactly 4 hashtags, got 3
- ... and 4 more (see report.json)

**v1 + mock-large** - 11 failing case(s)
- `tc04` (content_pack): expected exactly 4 hashtags, got 3
- `tc08` (content_pack): expected exactly 4 hashtags, got 3
- `tc12` (content_pack): expected exactly 4 hashtags, got 3
- `tc16` (content_pack): expected exactly 4 hashtags, got 3
- `tc20` (content_pack): expected exactly 4 hashtags, got 3
- `tc24` (content_pack): expected exactly 4 hashtags, got 3
- `tc28` (content_pack): expected exactly 4 hashtags, got 3
- `tc32` (content_pack): expected exactly 4 hashtags, got 3
- ... and 3 more (see report.json)

**v2 + mock-small** - 1 failing case(s)
- `tc45` (schedule): expected ok=True but got ok=False (all models failed after 1 attempts; last error: timeout on mock-small: mock-small exceeded 10.0s)

**v2 + mock-large** - 0 failing case(s)

**v2 + router (fallback on)** - 0 failing case(s)
