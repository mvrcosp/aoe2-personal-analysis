#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
gz_dir="${project_dir}/data/raw/api/gz"
replay_dir="${project_dir}/data/raw/aoe2rec"

mkdir -p -- "$gz_dir" "$replay_dir"

matches=(
    "507615992|https://rl0aoelivemk2blob.blob.core.windows.net/cloudfiles/433216/aoelive_/age2/replay/windows/4.0.0/0/M_507615992_1ea4630c29ff924547c65d3d47b2051e1c28fd927caa30a320cd6b8f07162f54.gz"
    "507613698|https://rl0aoelivemk2blob.blob.core.windows.net/cloudfiles/433216/aoelive_/age2/replay/windows/4.0.0/0/M_507613698_ea3740ca199af63901c87687c8ab742bb684ca0bc0cc47c50fe4b2ac7993994.gz"
    "507588718|https://rl0aoelivemk2blob.blob.core.windows.net/cloudfiles/433216/aoelive_/age2/replay/windows/4.0.0/0/M_507588718_c33594f8ce7c497a54a3d5fc7a01af582989468f2fcf1653d9044d1a6101cec1.gz"
    "507177338|https://rl0aoelivemk2blob.blob.core.windows.net/cloudfiles/433216/aoelive_/age2/replay/windows/4.0.0/0/M_507177338_f6e12106d4bd5588a287a624cf770d4ad25d2a0911b6b2b0ae5ba282cbac5de5.gz"
)

process_match() {
    local match_id="$1"
    local url="$2"
    local gz_name="${url##*/}"
    local gz_path="${gz_dir}/${gz_name}"
    local replay_path="${replay_dir}/AgeIIDE_Replay_${match_id}.aoe2record"
    local tmp_gz=""
    local tmp_replay=""

    if ! tmp_gz="$(mktemp "${gz_dir}/.${gz_name}.XXXXXX")"; then
        printf 'ERRO: não foi possível criar arquivo temporário para a partida %s.\n' "$match_id" >&2
        return 1
    fi
    if ! tmp_replay="$(mktemp "${replay_dir}/.AgeIIDE_Replay_${match_id}.XXXXXX")"; then
        printf 'ERRO: não foi possível criar arquivo temporário para a partida %s.\n' "$match_id" >&2
        rm -f -- "$tmp_gz"
        return 1
    fi

    printf 'Baixando partida %s...\n' "$match_id"
    if ! curl --fail --location --show-error --retry 3 --output "$tmp_gz" "$url"; then
        printf 'ERRO: download da partida %s falhou; seguindo para a próxima.\n' "$match_id" >&2
        rm -f -- "$tmp_gz" "$tmp_replay"
        return 1
    fi
    if ! gzip --test "$tmp_gz"; then
        printf 'ERRO: arquivo da partida %s não é um gzip válido; seguindo para a próxima.\n' "$match_id" >&2
        rm -f -- "$tmp_gz" "$tmp_replay"
        return 1
    fi
    if ! gzip --decompress --stdout "$tmp_gz" > "$tmp_replay"; then
        printf 'ERRO: não foi possível extrair a partida %s; seguindo para a próxima.\n' "$match_id" >&2
        rm -f -- "$tmp_gz" "$tmp_replay"
        return 1
    fi
    if ! mv -- "$tmp_gz" "$gz_path"; then
        printf 'ERRO: não foi possível salvar o gzip da partida %s; seguindo para a próxima.\n' "$match_id" >&2
        rm -f -- "$tmp_gz" "$tmp_replay"
        return 1
    fi
    if ! mv -- "$tmp_replay" "$replay_path"; then
        printf 'ERRO: não foi possível salvar o replay extraído da partida %s; seguindo para a próxima.\n' "$match_id" >&2
        rm -f -- "$tmp_replay"
        return 1
    fi

    printf 'GZ salvo em: %s\nReplay extraído em: %s\n' "$gz_path" "$replay_path"
}

failures=0
for match in "${matches[@]}"; do
    IFS='|' read -r match_id url <<< "$match"
    if ! process_match "$match_id" "$url"; then
        failures=$((failures + 1))
    fi
done

if (( failures > 0 )); then
    printf 'Concluído com %s falha(s); os demais downloads foram processados.\n' "$failures" >&2
    exit 1
fi
