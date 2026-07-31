class AnswerLengthEvaluator:
    def __init__(self, **_):
        pass

    def __call__(self, *, response: str = "", **_) -> dict:
        length = len(response)
        return {
            "score": length,
            "reason": f"Agent response contains {length} characters.",
        }
