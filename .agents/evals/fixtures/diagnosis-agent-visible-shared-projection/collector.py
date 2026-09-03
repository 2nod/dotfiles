from copy import deepcopy


def collect_prefix(engine, controllers, *, steps):
    """Collect controller-visible observations for a fixed non-terminal prefix."""
    seen = []
    for expected_step in range(steps):
        observations = [deepcopy(engine.state[position]) for position in range(2)]
        if any(observation.get("step") != expected_step for observation in observations):
            raise ValueError("engine step count drift")
        for controller, observation in zip(controllers, observations):
            controller(deepcopy(observation))
            seen.append(deepcopy(observation))
        engine.step()
    return seen
