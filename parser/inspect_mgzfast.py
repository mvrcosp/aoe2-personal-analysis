from mgz.fast.header import parse

with open("/home/mvrcosp/repos/aoe2-personal-analysis/data/raw/AgeIIDE_Replay_510406093.aoe2record", "rb") as f:
    header = parse(f)

print(header["version"])          # Version.DE
print(header["game_version"])     # e.g. "7.7"
print(header["save_version"])     # e.g. 13.34

print(header["scenario"]["map_id"])
print(header["lobby"]["seed"])
print(header["lobby"]["population"])
print(header["lobby"]["game_type_id"])
print(header["metadata"]["speed"])

'''for player in header["players"]:
    print(player["name"])
    print(player["civilization_id"])
    print(player["color_id"])
    print(player["position"])     # {"x": ..., "y": ...}'''

for de_player in header["de"]["players"]:
    print(de_player["name"])
    print(de_player["censored_name"])
    print(de_player["team_id"])

