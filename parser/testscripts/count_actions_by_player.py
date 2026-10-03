from collections import Counter
from mgz.model import parse_match

with open('/home/mvrcosp/repos/aoe2-personal-analysis/data/raw/AgeIIDE_Replay_510444990.aoe2record', 'rb') as data:
    match = parse_match(data)

counts = Counter(a.type for a in match.actions)
player_counts = Counter(
    (action.type, action.player.number if action.player is not None else None)
    for action in match.actions
)

players = {player.number: player.name for player in match.players}
player_numbers = sorted(players)
has_unassigned_actions = any(action.player is None for action in match.actions)

headers = ["Action", "Code", "Total"]
headers.extend(f"Player {number} ({players[number]})" for number in player_numbers)
if has_unassigned_actions:
    headers.append("Sem jogador")
print(" | ".join(headers))

for action in sorted(counts, key=lambda x: x.value):
    row = [action.name, str(action.value), str(counts[action])]
    row.extend(str(player_counts[(action, number)]) for number in player_numbers)
    if has_unassigned_actions:
        row.append(str(player_counts[(action, None)]))
    print(" | ".join(row))