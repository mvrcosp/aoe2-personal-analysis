from mgz.fast.header import parse
import logging

logging.basicConfig(level=logging.DEBUG)

REPLAY = "/home/mvrcosp/repos/aoe2-personal-analysis/data/raw/AgeIIDE_Replay_510444990.aoe2record"

with open(REPLAY, "rb") as f:
    header = parse(f)

print("=== REPLAY ===")
print("Version:", header["version"])
print("Game:", header["game_version"])
print("Save:", header["save_version"])
print("Log:", header["log_version"])

print("\n=== GAME ===")
print("Build:", header["de"]["build"])
#print("Map dimension:", header["de"]["map_dimension"])
print("RMS map ID:", header["de"]["rms_map_id"])
print("Speed:", header["de"]["speed"])
print("Population:", header["de"]["population_limit"])
print("Starting age:", header["de"]["starting_age_id"])
print("Ending age:", header["de"]["ending_age_id"])

print("\n=== PLAYERS ===")
for player in header["de"]["players"]:
    if player["number"] != -1:
        print(
            player["number"],
            player["name"],
            "civ=", player["civilization_id"],
            "color=", player["color_id"],
            "team=", player["team_id"],
        )

'''with open("", "rb") as f:
    header = parse(f)

print(header["version"])          # Version.DE
print(header["game_version"])     # e.g. "7.7"
print(header["save_version"])     # e.g. 13.34

print(header["scenario"]["map_id"])
print(header["lobby"]["seed"])
print(header["lobby"]["population"])
print(header["lobby"]["game_type_id"])
print(header["metadata"]["speed"])

for player in header["players"]:
    print(player["name"])
    print(player["civilization_id"])
    print(player["color_id"])
    print(player["position"])     # {"x": ..., "y": ...}

for de_player in header["de"]["players"]:
    print(de_player["name"])
    print(de_player["censored_name"])
    print(de_player["team_id"])'''

