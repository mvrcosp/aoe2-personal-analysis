import json
import re
from pathlib import Path

from mgz.model import parse_match, serialize

diretorio_projeto = Path(__file__).resolve().parent.parent
diretorio_origem = diretorio_projeto / "data" / "raw"
diretorio_destino = diretorio_projeto / "data" / "processed"
diretorio_destino.mkdir(parents=True, exist_ok=True)

arquivos_replay = sorted(diretorio_origem.glob("*.aoe2record"))
if not arquivos_replay:
    raise FileNotFoundError(f"Nenhum arquivo .aoe2record encontrado em: {diretorio_origem}")

for arquivo_origem in arquivos_replay:
    codigo_partida = re.search(r"(\d+)$", arquivo_origem.stem)
    if codigo_partida is None:
        raise ValueError(f"Não foi possível extrair o código da partida do nome: {arquivo_origem.name}")

    arquivo_destino = diretorio_destino / f"match_data_{codigo_partida.group(1)}.json"

    with arquivo_origem.open("rb") as replay:
        match = parse_match(replay)
        parsedmatchjson = json.dumps(serialize(match), indent=2)

    with arquivo_destino.open("w", encoding="utf-8") as json_file:
        json_file.write(parsedmatchjson)

    print(f"Arquivo salvo com sucesso em: {arquivo_destino}")
