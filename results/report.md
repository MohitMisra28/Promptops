# PromptOps comparison report

50 fixed test cases. Mock backends: latency is **simulated**, cost uses **hypothetical** price tables (small $0.0002/$0.0006, large $0.003/$0.015 per 1k tokens in/out).

| config | schema valid (first try) | schema valid (final) | instruction following | pass rate | mean latency s | p95 s | tokens | cost USD | retry | fallback |
|---|---|---|---|---|---|---|---|---|---|---|
| v1 + mock-small | 57% | 96% | 75% | 76% | 0.767 | 1.36 | 6870 | 0.00289 | 18% | 0% |
| v1 + mock-large | 94% | 98% | 77% | 78% | 2.057 | 2.784 | 5971 | 0.05869 | 4% | 0% |
| v2 + mock-small | 84% | 96% | 98% | 98% | 0.681 | 0.928 | 12713 | 0.00392 | 4% | 0% |
| v2 + mock-large | 94% | 98% | 100% | 100% | 2.063 | 2.784 | 12878 | 0.07973 | 4% | 0% |
| v2 + router (fallback on) | 84% | 100% | 75% | 74% | 3.547 | 5.96 | 18368 | 0.02391 | 16% | 4% |
| v1 + llama3.2:3b | 0% | 0% | 0% | 4% | 9.434 | 11.803 | 28940 | 0.0 | 98% | 0% |
| v2 + llama3.2:3b | 90% | 96% | 69% | 68% | 3.645 | 6.753 | 18119 | 0.0 | 10% | 0% |
| v3 + llama3.2:3b | 90% | 100% | 65% | 64% | 3.499 | 6.305 | 17897 | 0.0 | 10% | 0% |
| v4 + llama3.2:3b | 82% | 94% | 69% | 68% | 3.658 | 6.629 | 19676 | 0.0 | 16% | 0% |

## Is the cheaper model enough? (prompt v2, no fallback)

| task | small pass | large pass | small cost | large cost | verdict |
|---|---|---|---|---|---|
| announcement | 100% | 100% | 0.00076 | 0.01478 | small model is enough |
| content_pack | 100% | 100% | 0.00114 | 0.02377 | small model is enough |
| schedule | 93% | 100% | 0.00122 | 0.02567 | small model is NOT enough |
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
- `tc45` (schedule): expected ok=True but got ok=False (all models failed after 1 attempts; last error: timeout on mock-small: mock-small exceeded 90.0s)

**v2 + mock-large** - 0 failing case(s)

**v2 + router (fallback on)** - 13 failing case(s)
- `tc01` (schedule): expected >= 5 items, got 3
- `tc05` (schedule): missing keyword 'Jamshedpur'
- `tc07` (task_list): missing keyword 'cake'; expected >= 2 items, got 1
- `tc11` (task_list): missing keyword 'wifi'
- `tc19` (task_list): missing keyword 'sweets'
- `tc21` (schedule): expected >= 6 items, got 4
- `tc25` (schedule): expected >= 6 items, got 4
- `tc26` (announcement): missing keyword 'Kolkata'
- ... and 5 more (see report.json)

**v1 + llama3.2:3b** - 48 failing case(s)
- `tc01` (schedule): expected ok=True but got ok=False (all models failed after 3 attempts; last error: $: 'title' is a required property; $: 'date' is a required property; items/0: Additional properties are not allowed (' organizer', 'action', 'description', 'end', 'id', 'invitee', 'start', 'title' were unexpected))
- `tc02` (announcement): expected ok=True but got ok=False (all models failed after 3 attempts; last error: $: Additional properties are not allowed ('action', 'date', 'details', 'property', 'venue' were unexpected); $: 'headline' is a required property; $: 'body' is a required property)
- `tc03` (task_list): expected ok=True but got ok=False (all models failed after 3 attempts; last error: tasks/0: Additional properties are not allowed ('assignee', 'due_date', 'status' were unexpected); tasks/0: 'owner' is a required property; tasks/0: 'priority' is a required property)
- `tc04` (content_pack): expected ok=True but got ok=False (all models failed after 3 attempts; last error: $: 'summary' is a required property)
- `tc05` (schedule): expected ok=True but got ok=False (all models failed after 3 attempts; last error: $: 'title' is a required property; $: 'date' is a required property; items/0: Additional properties are not allowed ('date', 'details', 'name', 'tasks' were unexpected))
- `tc06` (announcement): expected ok=True but got ok=False (all models failed after 3 attempts; last error: $: Additional properties are not allowed ('date', 'event', 'time' were unexpected); $: 'headline' is a required property; $: 'body' is a required property)
- `tc07` (task_list): expected ok=True but got ok=False (all models failed after 3 attempts; last error: $: Additional properties are not allowed ('description', 'owner', 'preparer', 'task' were unexpected); $: 'tasks' is a required property)
- `tc08` (content_pack): expected ok=True but got ok=False (all models failed after 3 attempts; last error: $: Additional properties are not allowed ('actions' was unexpected); $: 'tweet' is a required property; $: 'email_subject' is a required property)
- ... and 40 more (see report.json)

**v2 + llama3.2:3b** - 16 failing case(s)
- `tc01` (schedule): expected >= 5 items, got 3
- `tc03` (task_list): missing keyword 'venue'
- `tc05` (schedule): missing keyword 'Jamshedpur'
- `tc07` (task_list): expected ok=True but got ok=False (all models failed after 3 attempts; last error: tasks/0: '{' is not of type 'object')
- `tc11` (task_list): missing keyword 'wifi'
- `tc19` (task_list): missing keyword 'sweets'
- `tc21` (schedule): expected >= 6 items, got 4
- `tc25` (schedule): expected >= 6 items, got 4
- ... and 8 more (see report.json)

**v3 + llama3.2:3b** - 18 failing case(s)
- `tc01` (schedule): expected >= 5 items, got 4
- `tc03` (task_list): missing keyword 'venue'
- `tc05` (schedule): expected >= 5 items, got 3
- `tc07` (task_list): missing keyword 'cake'; expected >= 2 items, got 1
- `tc11` (task_list): missing keyword 'wifi'
- `tc15` (task_list): missing keyword 'dashboard'
- `tc17` (schedule): missing keyword 'Ranchi'; expected >= 5 items, got 4
- `tc19` (task_list): missing keyword 'sweets'
- ... and 10 more (see report.json)

**v4 + llama3.2:3b** - 16 failing case(s)
- `tc01` (schedule): expected >= 5 items, got 3
- `tc03` (task_list): missing keyword 'venue'
- `tc05` (schedule): missing keyword 'Jamshedpur'
- `tc07` (task_list): expected ok=True but got ok=False (all models failed after 3 attempts; last error: tasks/0/priority: 'no priority specified' is not one of ['high', 'medium', 'low']; tasks/1/priority: 'urgent' is not one of ['high', 'medium', 'low']; tasks/2/priority: 'no priority specified' is not one of ['high', 'medium', 'low'])
- `tc11` (task_list): missing keyword 'wifi'
- `tc12` (content_pack): expected ok=True but got ok=False (all models failed after 1 attempts; last error: timeout on llama3.2:3b: timed out)
- `tc17` (schedule): missing keyword 'Ranchi'
- `tc19` (task_list): missing keyword 'sweets'
- ... and 8 more (see report.json)
