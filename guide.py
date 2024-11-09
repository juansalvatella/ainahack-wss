path_map = {
    1: {
        "x_path": '/html/body/div/header/div/div/div/div[2]/nav/div/div/ul/li[5]/button',
        "text": "Situacions de vida"
    },
    2: {
        "x_path": '/html/body/div/header/div/div/div/div[2]/nav/div/div/ul/li[5]/div/div[2]/div/div/div/div[2]/div/div/div/ul/li[6]/button',
        "text": "Mobilitat"
    },
    3: {
        "x_path": '/html/body/div/header/div/div/div/div[2]/nav/div/div/ul/li[5]/div/div[2]/div/div/div/div[2]/div/div/div/ul/li[6]/div/div/div[2]/div/div/div/ul/li/button',
        "text": "Em posen una multa de trànsit",
    },
    4: {
        "x_path": '/html/body/div/header/div/div/div/div[2]/nav/div/div/ul/li[5]/div/div[2]/div/div/div/div[2]/div/div/div/ul/li[6]/div/div/div[2]/div/div/div/ul/li/div/div/div[2]/div/div/div/ul/li[2]/p/a',
        "text": 'Accedeix a "Em posen una multa de trànsit"',
    },
    5: {"x_path": '/html/body/main/section/article/div/div/div/div/div[3]/div/div/div/p/a', "text": "consultar-la i fer el pagament", "pause": True},
    6: {"x_path": '/html/body/main/section/article/div/div/div/div/div/div[4]/div/div[2]/div/div/div/a', "text": "Inicia", "pause": True},
}

def get_step_by_path(x_path):
    for key, value in path_map.items():
        if value["x_path"] == x_path:
            return key  # Return the key as an integer
    return None  # If not found, return None

def handle_message(ws, message):
    try:
        test_res = {
            "x_path": path_map[1]["x_path"],
        }
        data = json.loads(message)
        if "x_path" in data:
            step = get_step_by_path(data["x_path"])
            if step:
                test_res["x_path"] = path_map[step]["x_path"]
        ws.send(json.dumps(test_res))
    except Exception as err:
        print("Error parsing message:", err)
