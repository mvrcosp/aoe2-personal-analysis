import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ZIP_DIRECTORY = PROJECT_DIR / "data" / "raw" / "zip"
DEFAULT_REPLAY_DIRECTORY = PROJECT_DIR / "data" / "raw" / "aoe2rec"
ZIP_NAME_PATTERN = re.compile(r"M_(\d+)\.zip\Z")


def find_zip_files(zip_directory: Path) -> list[Path]:
    return sorted(zip_directory.glob("M_*.zip"))


def extract_replay(zip_path: Path, replay_directory: Path) -> tuple[Path, bool]:
    match = ZIP_NAME_PATTERN.fullmatch(zip_path.name)
    if match is None:
        raise ValueError(f"Nome de ZIP inesperado: {zip_path.name}")

    match_id = match.group(1)
    replay_name = f"AgeIIDE_Replay_{match_id}.aoe2record"
    replay_directory.mkdir(parents=True, exist_ok=True)
    replay_path = replay_directory / replay_name
    temporary_path = None

    try:
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"O ZIP contém dados corrompidos: {zip_path}")

            replay_members = [
                member
                for member in archive.infolist()
                if member.filename == replay_name and not member.is_dir()
            ]
            if len(replay_members) != 1:
                raise ValueError(
                    f"{zip_path.name} precisa conter exatamente um "
                    f"{replay_name}; encontrados: {len(replay_members)}."
                )

            with tempfile.NamedTemporaryFile(
                dir=replay_directory,
                prefix=f".{replay_name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                with archive.open(replay_members[0]) as replay_data:
                    shutil.copyfileobj(replay_data, temporary_file)

        if replay_path.is_file() and replay_path.read_bytes() == temporary_path.read_bytes():
            temporary_path.unlink()
            temporary_path = None
            return replay_path, False

        temporary_path.replace(replay_path)
        temporary_path = None
        return replay_path, True
    except zipfile.BadZipFile as error:
        raise ValueError(f"Arquivo ZIP inválido: {zip_path}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def extract_zip_directory(
    zip_directory: Path = DEFAULT_ZIP_DIRECTORY,
    replay_directory: Path = DEFAULT_REPLAY_DIRECTORY,
    zip_paths: list[Path] | None = None,
) -> tuple[int, int, list[Path]]:
    zip_files = sorted(zip_paths) if zip_paths is not None else find_zip_files(zip_directory)
    if not zip_files:
        if zip_paths is not None:
            return 0, 0, []
        raise FileNotFoundError(f"Nenhum arquivo M_*.zip encontrado em {zip_directory}.")

    extracted = 0
    unchanged = 0
    failures = []
    for zip_path in zip_files:
        try:
            replay_path, was_written = extract_replay(zip_path, replay_directory)
        except (OSError, ValueError) as error:
            failures.append(zip_path)
            print(f"Falha ao extrair {zip_path.name}: {error}", file=sys.stderr)
            continue

        if was_written:
            extracted += 1
            print(f"Replay extraído: {replay_path}")
        else:
            unchanged += 1
            print(f"Replay já extraído e atualizado: {replay_path}")

    return extracted, unchanged, failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrai os replays dos ZIPs de data/raw/zip para data/raw/aoe2rec."
    )
    parser.add_argument(
        "--zip-directory",
        type=Path,
        default=DEFAULT_ZIP_DIRECTORY,
        help="Pasta dos ZIPs de replay.",
    )
    parser.add_argument(
        "--replay-directory",
        type=Path,
        default=DEFAULT_REPLAY_DIRECTORY,
        help="Pasta de destino dos arquivos .aoe2record.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    extracted, unchanged, failures = extract_zip_directory(
        zip_directory=args.zip_directory,
        replay_directory=args.replay_directory,
    )
    print(
        f"Resumo: {extracted} replay(s) extraído(s), "
        f"{unchanged} já estavam atualizados, {len(failures)} falha(s)."
    )
    if failures:
        raise RuntimeError(
            "Falha ao extrair ZIPs: " + ", ".join(path.name for path in failures)
        )


if __name__ == "__main__":
    main()
