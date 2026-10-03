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

## Converter os replays para JSON

Coloque os arquivos `.aoe2record` em `data/raw/aoe2rec/` e execute, a partir da raiz:

```bash
python -m parser.convert_replays_to_json
```

O script processa cada replay e grava o resultado em `data/processed/aoe2rec/match_data_{codigo}.json`. O código é o número no final do nome do replay, por exemplo, `AgeIIDE_Replay_510444990.aoe2record` gera `match_data_510444990.json`.

## Baixar replays recentes da API

Para baixar os quatro replays selecionados no histórico salvo, execute a partir da raiz:

```bash
bash parser/download_recent_replays.sh
```

O script salva os arquivos `.gz` em `data/raw/api/gz/` e extrai os `.aoe2record` em `data/raw/aoe2rec/`.

## Scripts Python

| Script | O que faz |
|---|---|
| `parser/convert_replays_to_json.py` | Processa todos os replays de `data/raw/aoe2rec/` e salva cada partida como JSON em `data/processed/aoe2rec/`. |
| `parser/testscripts/count_actions_by_player.py` | Conta as ações do replay por tipo e mostra o total e a divisão por jogador. |
| `parser/testscripts/calculate_replay_duration.py` | Soma os intervalos de sincronização do replay e imprime a duração estimada da partida em minutos. |
| `parser/testscripts/print_selected_replay_events.py` | Lê operações do replay em baixo nível e imprime eventos selecionados, como resignação, pesquisa, construção e chat. |
| `parser/testscripts/inspect_replay_header.py` | Inspeciona o cabeçalho do replay e imprime dados de versão, configuração da partida e jogadores. |
| `parser/testscripts/decode_replay_metadata.py` | Usa dados de referência de `aocref` para exibir informações decodificadas, como mapa, civilizações, cores e equipes. |

Os scripts de inspeção e análise individual ainda apontam para um replay específico; atualize o caminho no script para analisar outro arquivo em `data/raw/aoe2rec/`.
