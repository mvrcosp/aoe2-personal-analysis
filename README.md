# AoE2 Personal Analysis

Projeto de análise de replays do Age of Empires II: parseia arquivos `.aoe2record` e permite consultar informações da partida, como jogadores, ações e duração. O parse usa as bibliotecas `mgz` e `aocref`.

## Estrutura

- `data/raw/aoe2rec/`: replays de entrada (`.aoe2record`).
- `data/processed/aoe2rec/`: dados processados em JSON.
- `data/samples/`: pasta para arquivos de exemplo.
- `parser/`: scripts de leitura, conversão e inspeção dos replays.

Os arquivos de replay e os JSONs processados são ignorados pelo Git.

## Preparação

Na raiz do projeto, crie e ative um ambiente virtual e instale as dependências:

```bash
python -m venv env
source env/bin/activate
pip install -r parser/requirements.txt
```

## Pipeline de ingestão

Para executar o fluxo completo a partir da raiz do projeto:

```bash
python -m parser.ingest_recent_matches
```

Por padrão, consulta o perfil `612334`. Para outro perfil, use `--profile-id ID`. A frequência de chamadas e as tentativas de download podem ser ajustadas com `--delay-seconds`, `--retries` e `--timeout`.

O orquestrador chama as etapas nesta ordem:

1. **Consultar o histórico:** `parser.fetch_recent_match_history` chama `getRecentMatchHistory` e salva o payload em `data/raw/api/payload/payload_match_history_{TIMESTAMP_UTC}.json` e os IDs em `data/raw/api/matchIDs/matchIDs_match_history_{TIMESTAMP_UTC}.json`.
2. **Baixar os ZIPs:** `parser.download_match_replays` usa os IDs dessa consulta e baixa os arquivos para `data/raw/zip/`. Partidas com JSON processado válido são ignoradas; ZIPs já existentes e válidos também são reutilizados. Há uma pausa de 2 segundos entre requisições e até 3 tentativas para falhas transitórias.
3. **Extrair os replays:** `parser.extract_replay_zips` valida os ZIPs das partidas consultadas e extrai `AgeIIDE_Replay_{MATCH_ID}.aoe2record` para `data/raw/aoe2rec/`.
4. **Converter para JSON:** `parser.convert_replays_to_json` converte os replays disponíveis para `data/processed/aoe2rec/match_data_{MATCH_ID}.json`. JSONs já válidos são preservados; JSONs inválidos são gerados novamente.

O pipeline é incremental e pode ser reexecutado: mantém os arquivos já obtidos e tenta novamente as partidas ainda sem JSON processado. Se houver partidas indisponíveis ou falhas em alguma etapa, processa as demais e termina reportando os IDs que ficaram pendentes.

Cada etapa também pode ser executada isoladamente, na mesma ordem:

```bash
python -m parser.fetch_recent_match_history
python -m parser.download_match_replays
python -m parser.extract_replay_zips
python -m parser.convert_replays_to_json
```

Para o conversor isolado, os arquivos `.aoe2record` precisam estar em `data/raw/aoe2rec/`. Ele grava `match_data_{MATCH_ID}.json` em `data/processed/aoe2rec/`.

## APIs externas usadas pelo pipeline

| API/endpoint | Objetivo | Script que utiliza |
|---|---|---|
| `https://aoe-api.worldsedgelink.com/community/leaderboard/getRecentMatchHistory` | Obter o histórico recente do perfil e os IDs das partidas. | `parser.fetch_recent_match_history` (chamado pelo orquestrador). |
| `https://aoe.ms/replay/?gameId={MATCH_ID}&profileId={PROFILE_ID}` | Solicitar o replay associado à partida e à perspectiva do perfil. Redireciona para a API oficial de replays da Microsoft, que retorna um ZIP contendo o `.aoe2record`. | `parser.download_match_replays` (chamado pelo orquestrador). |
| `https://api.ageofempires.com/api/GameStats/AgeII/GetMatchReplay/` | Endpoint de destino do redirecionamento de `aoe.ms`; entrega o arquivo ZIP de replay quando ele está disponível. | Acessado indiretamente por `parser.download_match_replays`. |

Nem todos os replays estão disponíveis para download: a API pode responder `404`. O script registra essas falhas, continua com as outras partidas e deixa as partidas sem JSON prontas para uma tentativa futura. Os passos de extração e conversão são locais e não chamam APIs externas.

## Exportar partidas recentes para CSV

Para filtrar o histórico do perfil `612334` entre 2 e 4 de outubro de 2026 e gerar uma tabela CSV, execute a partir da raiz:

```bash
python -m parser.export_match_history_csv
```

Por padrão, o script lê `data/raw/api/api_match_history_612334_2.json` e grava `data/processed/api/match_history_612334_2026-10-02_2026-10-04.csv`. As datas e horas são interpretadas e exibidas no fuso `America/Sao_Paulo`. Também é possível informar outros caminhos, perfil, datas e fuso com `--input`, `--output`, `--profile-id`, `--start-date`, `--end-date` e `--timezone`.

## Scripts Python

| Script | O que faz |
|---|---|
| `parser/convert_replays_to_json.py` | Converte os replays de `data/raw/aoe2rec/` para JSON em `data/processed/aoe2rec/`, ignorando saídas já válidas. |
| `parser/download_match_replays.py` | Baixa os ZIPs das partidas ainda não processadas usando um JSON de IDs. |
| `parser/extract_replay_zips.py` | Valida e extrai os arquivos `.aoe2record` dos ZIPs em `data/raw/zip/`. |
| `parser/fetch_recent_match_history.py` | Consulta o histórico recente pela API e salva o payload e os IDs das partidas em arquivos JSON. |
| `parser/ingest_recent_matches.py` | Orquestra as quatro etapas do pipeline de ingestão. |
| `parser/export_match_history_csv.py` | Filtra um histórico de partidas da API por perfil e intervalo de datas e o exporta para CSV. |
| `parser/testscripts/count_actions_by_player.py` | Conta as ações do replay por tipo e mostra o total e a divisão por jogador. |
| `parser/testscripts/calculate_replay_duration.py` | Soma os intervalos de sincronização do replay e imprime a duração estimada da partida em minutos. |
| `parser/testscripts/print_selected_replay_events.py` | Lê operações do replay em baixo nível e imprime eventos selecionados, como resignação, pesquisa, construção e chat. |
| `parser/testscripts/inspect_replay_header.py` | Inspeciona o cabeçalho do replay e imprime dados de versão, configuração da partida e jogadores. |
| `parser/testscripts/decode_replay_metadata.py` | Usa dados de referência de `aocref` para exibir informações decodificadas, como mapa, civilizações, cores e equipes. |

Os scripts de inspeção e análise individual ainda apontam para um replay específico; atualize o caminho no script para analisar outro arquivo em `data/raw/aoe2rec/`.
