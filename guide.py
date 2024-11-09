path_map = {
    1: {
        "x_path": '//*[@id="hTContainer"]/div/div[1]/div[2]/nav/div/div/ul/li[5]/button',
        "text": "Situacions de vida"
    },
    2: {
        "x_path": '//*[@id="hTContainer"]/div/div[1]/div[2]/nav/div/div/ul/li[5]/div/div[2]/div[1]/div/div[1]/div[2]/div/div/div/ul/li[6]/button',
        "text": "Mobilitat"
    },
    3: {
        "x_path": '//*[@id="hTContainer"]/div/div[1]/div[2]/nav/div/div/ul/li[5]/div/div[2]/div[1]/div/div[1]/div[2]/div/div/div/ul/li[6]/div/div[1]/div[2]/div/div/div/ul/li[1]/a',
        "text": "Em posen una multa de trànsit",
    },
    4: {
        "x_path": '//*[@id="hTContainer"]/div/div[1]/div[2]/nav/div/div/ul/li[5]/div/div[2]/div[1]/div/div[1]/div[2]/div/div/div/ul/li[6]/div/div[1]/div[2]/div/div/div/ul/li[1]/div/div[1]/div[2]/div/div/div/ul/li[2]/p/a',
        "text": 'Accedeix a "Em posen una multa de trànsit"',
    },
    5: {"x_path": '//*[@id="c9c5d0b8-e18f-11ec-b15b-005056924a59"]/div[3]/div/div/div/p[1]/a', "text": "consultar-la i fer el pagament"},
    6: {"x_path": '//*[@id="detall"]/div/div/div[4]/div[1]/div[2]/div/div[1]/div[1]/a', "text": "Inicia"},
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
