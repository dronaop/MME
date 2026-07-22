def eligibility_lines(records, score_pct):
    if score_pct is None:
        return []
    lines = []
    for r in records:
        eligible = r["last_year_cutoff_pct"] <= score_pct
        lines.append(
            f"[{r['college_id']}] ELIGIBILITY CHECK (code-verified, trust this over your "
            f"own arithmetic): student score {score_pct}% vs cutoff {r['last_year_cutoff_pct']}% "
            f"-> {'ELIGIBLE' if eligible else 'NOT ELIGIBLE'}"
        )
    return lines


def budget_conversion_lines(records, budget_amount, budget_period):
    if budget_amount is None or budget_period is None:
        return []
    lines = []
    for r in records:
        annual = r["annual_fees_inr"]
        if budget_period == "year":
            comparable, note = annual, "annual fee, compared directly"
        elif budget_period == "semester":
            comparable = annual / 2
            note = "annual fee / 2 — assumes 2 semesters/year (not stated in the data; flagged as an assumption)"
        elif budget_period == "total_course":
            comparable, note = None, "course duration is not in the dataset — cannot reliably convert to a total; flag this to the student"
        else:
            comparable, note = annual, "unrecognized period, treated as annual"

        if comparable is not None:
            within = comparable <= budget_amount
            lines.append(
                f"[{r['college_id']}] BUDGET CHECK (code-verified): tuition Rs {comparable:,.0f} "
                f"per {budget_period} ({note}) vs stated budget Rs {budget_amount:,.0f} "
                f"-> {'WITHIN BUDGET' if within else 'OVER BUDGET'} on tuition alone — "
                f"check this college's 'about' text for hostel/mess/kit charges on top of this"
            )
        else:
            lines.append(f"[{r['college_id']}] BUDGET CHECK: {note}")
    return lines


def no_match_signal(all_records, parsed):

    name = parsed.get("mentioned_college_name")
    if not name:
        return None
    name_lower = name.lower()
    for r in all_records:
        if name_lower in r["name"].lower() or r["name"].lower() in name_lower:
            return None 
    return f"No college matching '{name}' was found in the dataset."
