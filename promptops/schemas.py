"""JSON Schemas for each supported task. Structural only; instruction-following is checked separately."""
_str = {"type": "string", "minLength": 1}

SCHEMAS: dict[str, dict] = {
    "schedule": {
        "type": "object", "additionalProperties": False, "required": ["title", "date", "items"],
        "properties": {"title": _str, "date": _str, "items": {"type": "array", "minItems": 1, "items": {
            "type": "object", "additionalProperties": False, "required": ["time", "activity"],
            "properties": {"time": _str, "activity": _str}}}},
    },
    "announcement": {
        "type": "object", "additionalProperties": False, "required": ["headline", "body", "call_to_action"],
        "properties": {"headline": _str, "body": _str, "call_to_action": _str},
    },
    "task_list": {
        "type": "object", "additionalProperties": False, "required": ["tasks"],
        "properties": {"tasks": {"type": "array", "minItems": 1, "items": {
            "type": "object", "additionalProperties": False, "required": ["task", "owner", "priority"],
            "properties": {"task": _str, "owner": _str, "priority": {"enum": ["high", "medium", "low"]}}}}},
    },
    "content_pack": {
        "type": "object", "additionalProperties": False, "required": ["tweet", "email_subject", "summary", "hashtags"],
        "properties": {"tweet": _str, "email_subject": _str, "summary": _str,
                       "hashtags": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^#\\w+$"}}},
    },
}
