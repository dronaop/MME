import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from src.llm_client import call_llm
from src.debug import log


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(_PROJECT_ROOT / "templates"),
    autoescape=False,
)


def _parse_system_prompt(question: str) -> str:
    return _TEMPLATE_ENV.get_template("parse_prompt.jinja").render(question=question)

_DEFAULTS = {
    "mentioned_college_name": None,
    "student_score_pct": None,
    "budget_amount_inr": None,
    "budget_period": None,
    "course_keyword": None,
    "wants_government_only": None,
    "wants_hostel": None,
    "is_listing_question": False,
}


def parse_query(question: str) -> dict:
    out = dict(_DEFAULTS)
    try:
        system_prompt = _parse_system_prompt(question)
        result = call_llm(system_prompt, "Return the JSON object.")
        log("query-parser result", {
            "text": result.text,
        })
        parsed = json.loads(result.text)
        for k in out:
            if k in parsed and parsed[k] is not None:
                out[k] = parsed[k]
    except Exception as exc:
        log("$$ query-parser failure (using defaults)", repr(exc))
    return out
