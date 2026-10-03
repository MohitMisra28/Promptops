"""Generate data/test_cases.json: 40 happy-path cases (10 messy briefs x 4 tasks) + 10 adversarial cases."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# (title, place keyword, schedule/agenda items, owner actions, task keyword)
EVENTS = [
    ("Team offsite in Pune on 3 March", "Pune", ["kickoff at 10am", "lunch at 1pm", "demo at 3:30pm"], ["Priya books venue", "Rahul sends invites by Friday"], "venue"),
    ("Product launch party at Jamshedpur on 12 June", "Jamshedpur", ["doors open 6pm", "keynote at 7pm", "dinner at 8:30pm"], ["Asha orders cake urgent", "Dev prepares slides"], "cake"),
    ("Hackathon at IIT Delhi on 21 April", "Delhi", ["registration 9am", "coding starts 10am", "judging 5pm", "awards 6:30pm"], ["Meera arranges wifi asap", "Karan collects laptops", "Isha prints badges"], "wifi"),
    ("Quarterly review in Mumbai on 5 July", "Mumbai", ["welcome 9:30am", "metrics review 10am", "roadmap 2pm"], ["Nikhil updates dashboard critical", "Sana books cab"], "dashboard"),
    ("Diwali potluck in Ranchi on 1 November", "Ranchi", ["setup 4pm", "puja 6pm", "dinner 7:30pm"], ["Tara brings sweets", "Vikram arranges lights optional"], "sweets"),
    ("Customer workshop in Bengaluru on 18 September", "Bengaluru", ["intro 11am", "hands-on lab 12pm", "lunch 1:30pm", "Q&A 3pm"], ["Lena sends agenda", "Omar tests demo environment urgent"], "demo"),
    ("Annual sports day in Kolkata on 9 December", "Kolkata", ["march past 8am", "relay 9am", "tug of war 11am", "prize giving 1pm"], ["Rohan marks the track", "Pooja orders trophies by Monday"], "trophies"),
    ("Board meeting in Chennai on 30 August", "Chennai", ["coffee 9am", "financials 9:30am", "strategy 11am"], ["Gita circulates minutes", "Arun books room deadline"], "minutes"),
    ("Open mic night in Goa on 14 February", "Goa", ["sound check 5pm", "doors 7pm", "first act 7:30pm", "headliner 9pm"], ["Zoya hires sound crew", "Ben designs posters", "Uma sells tickets"], "posters"),
    ("Onboarding day for new interns in Hyderabad on 2 January", "Hyderabad", ["welcome 10am", "HR session 11am", "tools setup 12pm", "team lunch 1pm", "mentor pairing 3pm", "wrap-up 4:30pm"], ["Farah prepares laptops asap", "Gaurav schedules mentors", "Hema orders lunch"], "laptops"),
]


def build():
    cases, n = [], 0

    def add(task, text, expect, tags, **kw):
        nonlocal n
        n += 1
        cases.append({"id": f"tc{n:02d}", "task": task, "input": text, "expect": expect, "tags": tags, **kw})

    for title, place, items, acts, kw in EVENTS:
        body = ". ".join(items + acts)
        add("schedule", f"{title}. {body}.", {"must_contain": [place], "min_items": len(items) + len(acts)}, ["happy", "schedule"])
        add("announcement", f"{title}. {body}. Keep the body under 25 words.", {"must_contain": [place], "max_body_words": 25}, ["happy", "constraint"])
        add("task_list", f"{title}. {'. '.join(acts)}.", {"must_contain": [kw], "min_items": len(acts)}, ["happy", "task_list"])
        add("content_pack", f"{title}. {body}. Use exactly 4 hashtags.", {"must_contain": [place], "hashtags": 4, "tweet_max": 280}, ["happy", "constraint"])

    add("schedule", "Design review on 4 May. kickoff 10am. [[MALFORMED]] wrap-up 11am.", {"must_contain": ["design"], "min_items": 2}, ["edge", "malformed_json"])
    add("content_pack", "Launch webinar on 8 August. Demo at 4pm. Q&A at 5pm. Use exactly 3 hashtags. [[MALFORMED]]", {"hashtags": 3, "must_contain": ["webinar"]}, ["edge", "malformed_json"])
    add("announcement", "Office move to Salt Lake on 1 October. Packing starts Monday. Write a short announcement. Make it long and detailed. Keep the body under 20 words.",
        {"must_contain": ["salt lake"], "max_body_words": 20, "warning": "contradict"}, ["edge", "contradictory"])
    add("task_list", "Annual audit in Noida. Be brief. Give a comprehensive and detailed breakdown. Sam collects invoices urgent. Lia books auditors.",
        {"must_contain": ["invoices"], "warning": "contradict"}, ["edge", "contradictory"])
    add("schedule", "Retro in Pune on 6 June. standup 9am. [[TIMEOUT]] review 11am.", {"must_contain": ["pune"]}, ["edge", "timeout_fallback"])
    add("announcement", "Server maintenance on 3 March. [[TIMEOUT_ALL]] Downtime 2am to 4am.", {"ok": False, "error_contains": "timeout"}, ["edge", "timeout_all"])
    add("schedule", "Webinar in Jaipur on 7 July. intro 3pm. demo 3:30pm. wrap-up 4:30pm. [[INTERRUPT]]", {"must_contain": ["jaipur"], "min_items": 3, "warning": "interrupted"}, ["edge", "interrupted_stream"], stream=True)
    add("schedule", "Diwali मेला at Jamshedpur on 12 November. Stalls open 5pm. Music at 7pm.", {"must_contain": ["jamshedpur", "मेला"], "min_items": 2}, ["edge", "unicode"])
    add("task_list", "   ", {"ok": False, "error_contains": "empty"}, ["edge", "empty_input"])
    add("task_list", "- Standup 9am\n- Ravi fixes login bug asap\n- Mia writes release notes\n- Retro at 4pm", {"must_contain": ["login"], "min_items": 3}, ["edge", "noisy_bullets"])
    return cases


if __name__ == "__main__":
    cases = build()
    out = pathlib.Path(__file__).resolve().parent.parent / "data" / "test_cases.json"
    out.write_text(json.dumps(cases, indent=1, ensure_ascii=False))
    print(len(cases), "cases ->", out)
