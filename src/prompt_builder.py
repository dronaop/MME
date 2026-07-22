from pathlib import Path
from jinja2 import Environment, FileSystemLoader


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(_PROJECT_ROOT / "templates"),
    autoescape=False,
)


def _system_prompt() -> str:
    return _TEMPLATE_ENV.get_template("system_prompt.jinja").render()

def format_record(r):
    courses = "; ".join(r["courses_offered"])
    hostel = "Yes" if r["hostel_available"] else "No"
    placement = "0 (not reported/applicable)" if r["avg_placement_lpa"] == 0 else r["avg_placement_lpa"]
    return (
        f"[{r['college_id']}] {r['name']} — {r['city']}, {r['state']} ({r['type']})\n"
        f"  Courses: {courses}\n"
        f"  Annual fees: Rs {r['annual_fees_inr']:,}/year | Cutoff: {r['last_year_cutoff_pct']}% | "
        f"Seats: {r['total_seats']} | Hostel: {hostel} | NAAC: {r['naac_grade']} | "
        f"Avg placement: {placement} LPA | Established: {r['established_year']}\n"
        f"  About: {r['about']}"
    )


def build_messages(question, retrieved_records, check_lines=None):
    context = "\n\n".join(format_record(r) for r in retrieved_records)
    checks_block = ""
    if check_lines:
        checks_block = (
            "\n\nCODE-VERIFIED CHECKS — these numbers were computed in Python, not by "
            "you. Trust them over redoing the arithmetic yourself:\n" + "\n".join(check_lines)
        )
    user_prompt = (
        f"RETRIEVED COLLEGE RECORDS:\n\n{context}{checks_block}\n\n"
        f"STUDENT QUESTION: {question}\n\n"
        "Respond with the JSON object only, per the rules above."
    )
    return _system_prompt(), user_prompt
