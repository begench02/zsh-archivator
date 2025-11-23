import argparse
import os
import tarfile
import time
from typing import Optional

from compression import zstd  

CHUNK_SIZE = 64 * 1024 

def ensure_zst_extension(path: str) -> None:
    if not path.lower().endswith(".zst"):
        raise SystemExit(
            f"Неверное расширение архива: {path!r}. "
            "Поддерживается только формат .zst (zstd)."
        )


def dir_size(root: str) -> int:
    total = 0
    for base, _, files in os.walk(root):
        for name in files:
            fp = os.path.join(base, name)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def strip_zst_suffix(name: str) -> str:
    return name[:-4] if name.lower().endswith(".zst") else name


def compress_file_zstd(source: str, archive: str) -> None:
    with open(source, "rb") as f_in, zstd.open(archive, "wb") as f_out:
        while True:
            chunk = f_in.read(CHUNK_SIZE)
            if not chunk:
                break
            f_out.write(chunk)

    print(f"Создан архив (zst): {os.path.abspath(archive)}")


def compress_directory_zstd(source: str, archive: str) -> None:
    with tarfile.open(archive, mode="w:zst") as tar:
        base = os.path.abspath(source)
        parent = os.path.dirname(base)
        for root, _, files in os.walk(base):
            for name in files:
                full = os.path.join(root, name)
                arcname = os.path.relpath(full, start=parent)
                tar.add(full, arcname=arcname)

    print(f"Создан tar+zst архив: {os.path.abspath(archive)}")


def compress(source: str, archive: str, benchmark: bool) -> None:
    ensure_zst_extension(archive)

    if not os.path.exists(source):
        raise SystemExit(f"Источник не найден: {source!r}")

    start = time.perf_counter()

    if os.path.isdir(source):
        compress_directory_zstd(source, archive)
    else:
        compress_file_zstd(source, archive)

    if benchmark:
        elapsed = time.perf_counter() - start
        print(f"Время выполнения: {elapsed:.3f} сек.")


def decompress_regular_zstd(archive: str, destination: str) -> str:
    if os.path.isdir(destination):
        base = os.path.basename(archive)
        out_path = os.path.join(destination, strip_zst_suffix(base))
    else:
        out_path = destination

    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with zstd.open(archive, "rb") as f_in, open(out_path, "wb") as f_out:
        while True:
            chunk = f_in.read(CHUNK_SIZE)
            if not chunk:
                break
            f_out.write(chunk)

    print(f"Распакованный файл сохранён в: {os.path.abspath(out_path)}")
    return out_path


def decompress(archive: str, destination: str, benchmark: bool) -> None:
    ensure_zst_extension(archive)

    if not os.path.exists(archive):
        raise SystemExit(f"Архив не найден: {archive!r}")

    start = time.perf_counter()

    is_tar = False
    try:
        with tarfile.open(archive, mode="r:*") as tar:
            tar.getmembers()
            is_tar = True
    except tarfile.ReadError:
        is_tar = False

    if is_tar:
        if not os.path.isdir(destination):
            os.makedirs(destination, exist_ok=True)

        with tarfile.open(archive, mode="r:*") as tar:
            tar.extractall(destination)

        print(f"tar+zst архив распакован в директорию: {os.path.abspath(destination)}")
    else:
        decompress_regular_zstd(archive, destination)

    if benchmark:
        elapsed = time.perf_counter() - start
        print(f"Время выполнения: {elapsed:.3f} сек.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Простой архиватор/распаковщик на zstd (.zst). "
                    "Для директорий используется tarfile + zstd."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_compress = subparsers.add_parser("compress", help="Архивировать файл или директорию в .zst")
    p_compress.add_argument("source")
    p_compress.add_argument("archive")
    p_compress.add_argument("-b", "--benchmark", action="store_true")

    p_extract = subparsers.add_parser("extract", help="Распаковать .zst архив")
    p_extract.add_argument("archive")
    p_extract.add_argument("destination", nargs="?", default=".")
    p_extract.add_argument("-b", "--benchmark", action="store_true")

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "compress":
        compress(args.source, args.archive, args.benchmark)
    elif args.command == "extract":
        decompress(args.archive, args.destination, args.benchmark)


if __name__ == "__main__":
    main()
