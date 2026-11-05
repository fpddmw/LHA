"""One explicit submission per stateless LHA model request."""

NAMESPACE = "lha"
SUBMIT = "submit_result"
INSTRUCTION = (
    "Submit this step's complete requested response through lha.submit_result once. "
    "Use its input for the requested JSON object or text, without an extra wrapper. "
    "For an operation, submit one operation and yield: LHA executes it and supplies "
    "the actual result in the next request."
)


def apply_contract(body):
    body["instructions"] += "\n\n" + INSTRUCTION
    body["tools"] = [{
        "type": "namespace", "name": NAMESPACE,
        "description": "Submit a response to the LHA host.",
        "tools": [{
            "type": "custom", "name": SUBMIT,
            "description": "Submit the complete response requested for this step. "
                "The input is exactly that response, including all action arguments "
                "when an operation is requested.",
            "format": {"type": "text"},
        }],
    }]
    body["tool_choice"] = "required"
    body["parallel_tool_calls"] = False


def is_submission(item):
    return (item.get("type") == "custom_tool_call"
            and (item.get("name"), item.get("namespace")) in {
                (SUBMIT, NAMESPACE), (NAMESPACE + "." + SUBMIT, None),
            })
