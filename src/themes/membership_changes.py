def calculate_membership_changes(communities: dict) -> dict:
    """
    Calculates existing, new, and lost members over time for a given path of communities.

    Args:
        communities: Dictionary of month -> list of members
    """
    results = {}
    prev_members = set()
    seen_members = set()

    for month, members in communities.items():
        current_members = set(members)

        if len(prev_members) == 0:
            new_members = set()
            lost_members = set()
            existing_members = current_members
            reappearing_members = set()
        else:
            new_members = current_members - prev_members
            lost_members = prev_members - current_members
            existing_members = current_members & prev_members
            reappearing_members = (current_members & seen_members) - prev_members

        results[month] = {
            'members': list(current_members),
            'existing_members': list(existing_members),
            'new_members': list(new_members),
            'lost_members': list(lost_members),
            'reappearing_members': list(reappearing_members)
        }

        seen_members.update(current_members)
        prev_members = current_members

    return results
