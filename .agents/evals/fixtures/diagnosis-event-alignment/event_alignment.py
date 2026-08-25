def labels_for_observations(steps):
    """Return the current and following actions for each observation.

    An action stored on step N was selected from the observation on step N - 1.
    """
    rows = []
    for index, step in enumerate(steps):
        rows.append(
            {
                "observation": step["observation"],
                "action_t0": step.get("action"),
                "action_t1": steps[index + 1].get("action") if index + 1 < len(steps) else None,
            }
        )
    return rows
