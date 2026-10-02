from pathlib import Path
import json

import aocref
from mgz.fast.header import parse


REPLAY = (
    Path(__file__).parent.parent
    / "data"
    / "raw"
    / "AgeIIDE_Replay_510444990.aoe2record"
)


def load_dataset():
    """Load AoE2 DE reference data."""
    aocref_path = Path(aocref.__file__).parent
    dataset_path = aocref_path / "data" / "datasets" / "100.json"

    with dataset_path.open(encoding="utf-8") as file:
        return json.load(file)


def load_constants():
    """Load common AoE2 reference data."""
    aocref_path = Path(aocref.__file__).parent
    constants_path = aocref_path / "data" / "constants.json"

    with constants_path.open(encoding="utf-8") as file:
        return json.load(file)


def decode_player(player, dataset, constants):
    civilization_id = str(player["civilization_id"])
    color_id = str(player["color_id"])

    civilization = dataset["civilizations"].get(civilization_id, {})
    civilization_name = civilization.get("name", f"Unknown ({civilization_id})")

    color_name = constants["player_colors"].get(
        color_id,
        f"Unknown ({color_id})",
    )
    
    return {
        "name": player["name"].decode("utf-8"),
        "civilization": civilization_name,
        "civilization_id": player["civilization_id"],
        "color": color_name,
        "color_id": player["color_id"],
        "team": player["team_id"],
    }

def extract_map_name(instructions):
    text = instructions.decode("utf-8")

    for line in text.splitlines():
        if line.startswith("Location:"):
            return line.split(":", 1)[1].strip()

    return "Unknown"

def main():
    dataset = load_dataset()
    constants = load_constants()

    with REPLAY.open("rb") as file:
        replay = parse(file)

    print("=== REPLAY ===")
    print(f"Version: {replay['version']}")
    print(f"Game: {replay['game_version']}")
    print(f"Save: {replay['save_version']}")
    print(f"Log: {replay['log_version']}")

    de = replay["de"]

    map_name = extract_map_name(replay["scenario"]["instructions"])
    print("\n=== GAME ===")
    print(f"Build: {de['build']}")
    print(f"Map: {map_name}")
    print(f"Map size: {replay['map']['dimension']}")
    print(f"RMS map ID: {de['rms_map_id']}")
    print(f"Speed: {de['speed']}")
    print(f"Population: {de['population_limit']}")

    print("\n=== PLAYERS ===")

    for player in de["players"]:
        if player["number"] == -1:
            continue

        decoded = decode_player(player, dataset, constants)

        print(
            f"{decoded['name']} | "
            f"{decoded['civilization']} | "
            f"team={decoded['team']} | "
            f"color={decoded['color']}"
        )


if __name__ == "__main__":
    main()