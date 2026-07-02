from src.themes.membership_changes import calculate_membership_changes


def test_calculate_membership_changes_tracks_new_lost_existing_and_reappearing():
    changes = calculate_membership_changes(
        {
            "january_0": [1, 2],
            "february_0": [2, 3],
            "march_0": [1, 3],
        }
    )

    assert set(changes["january_0"]["existing_members"]) == {1, 2}
    assert set(changes["february_0"]["existing_members"]) == {2}
    assert set(changes["february_0"]["new_members"]) == {3}
    assert set(changes["february_0"]["lost_members"]) == {1}
    assert set(changes["march_0"]["reappearing_members"]) == {1}
