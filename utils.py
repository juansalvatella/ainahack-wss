ACTION_HOOK = "ws://120.86.175.34.bc.googleusercontent.com/jambonz-websocket"

def gather_data(text: str):
    return {
        "input": ["speech"],
        "verb": "gather",
        "say": {
            "text": text,
        },
        "actionHook": ACTION_HOOK
    }
