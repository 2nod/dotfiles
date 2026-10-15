def summarize(calls):
    return {
        "execution_complete": all(call["status"] == "completed" for call in calls),
        "visual_inputs": sum(call["tool"] == "screenshot" for call in calls),
        "responses_complete": True,
    }
