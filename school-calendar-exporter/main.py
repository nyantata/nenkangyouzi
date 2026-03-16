#!/usr/bin/env python3
"""
School Calendar Exporter
年間行事計画ファイル（PDF/Excel/CSV）をカレンダー形式にエクスポートするCLIツール。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Load .env before any other imports that use env vars
load_dotenv()

from src.ai.analyzer import Analyzer
from src.exporter.csv_exporter import export_csv
from src.exporter.ics_exporter import export_ics
from src.parser import get_parser
from src.ui.selector import (
    display_events_table,
    filter_events,
    review_step,
    select_categories,
    select_grades,
    select_output_format,
)
from src.utils.cache import load_cache, save_cache
from src.utils.logger import get_logger

console = Console()
logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent
CATEGORIES_FILE = BASE_DIR / "categories.json"
OUTPUT_DIR = BASE_DIR / "output"


def load_categories() -> list[dict]:
    with open(CATEGORIES_FILE, encoding="utf-8") as f:
        return json.load(f)["categories"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="年間行事計画ファイルをGoogleカレンダー等にエクスポートします。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="入力ファイルパス（PDF / Excel / CSV）",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="キャッシュを使用せず強制的に再解析する",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"出力ディレクトリ（デフォルト: {OUTPUT_DIR}）",
    )
    return parser.parse_args()


def get_input_file(args: argparse.Namespace) -> str:
    if args.file:
        return args.file

    import questionary
    file_path = questionary.path(
        "入力ファイルのパスを入力してください（PDF / Excel / CSV）:",
    ).ask()
    if not file_path:
        console.print("[red]ファイルパスが指定されていません。終了します。[/red]")
        sys.exit(1)
    return file_path


def resolve_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        console.print(
            "[red]ANTHROPIC_API_KEY が設定されていません。\n"
            ".env ファイルに ANTHROPIC_API_KEY=<your_key> を追記してください。[/red]"
        )
        sys.exit(1)
    return key


def run_analysis(
    file_path: str,
    categories: list[dict],
    api_key: str,
    use_cache: bool,
) -> list[dict]:
    """Extract text, optionally use cache, run AI analysis."""
    if use_cache:
        cached = load_cache(file_path)
        if cached is not None:
            console.print("[green]キャッシュから行事データを読み込みました。[/green]")
            return cached

    console.print(f"[cyan]ファイルを解析中: {file_path}[/cyan]")
    parser = get_parser(file_path)
    text = parser.extract_text(file_path)

    if not text.strip():
        console.print("[red]テキストを抽出できませんでした。ファイルを確認してください。[/red]")
        sys.exit(1)

    console.print(
        f"[dim]テキスト抽出完了: {len(text)} 文字。Claude APIで解析中...[/dim]"
    )
    analyzer = Analyzer(api_key=api_key)
    events = analyzer.analyze(text, categories)

    if use_cache:
        save_cache(file_path, events)

    return events


def build_output_path(output_dir: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return str(Path(output_dir) / f"calendar_{ts}.{ext}")


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]年間行事計画 → カレンダーエクスポートツール[/bold cyan]",
            border_style="cyan",
        )
    )

    args = parse_args()
    file_path = get_input_file(args)

    if not Path(file_path).exists():
        console.print(f"[red]ファイルが見つかりません: {file_path}[/red]")
        sys.exit(1)

    api_key = resolve_api_key()
    categories = load_categories()

    # --- Analysis loop (supports re-analysis) ---
    events: list[dict] = []
    while True:
        events = run_analysis(
            file_path,
            categories,
            api_key,
            use_cache=not args.no_cache,
        )

        if not events:
            console.print("[yellow]行事データが抽出できませんでした。[/yellow]")
            sys.exit(1)

        console.print(f"\n[green]{len(events)} 件の行事を検出しました。[/green]\n")

        # Review step
        reviewed = review_step(events)
        if reviewed:  # Non-empty means approved or edited
            events = reviewed
            break
        # Empty means user chose re-analysis
        console.print("[yellow]再解析を行います（キャッシュを無視）...[/yellow]")
        args.no_cache = True  # Force re-analysis next iteration

    # --- Category & grade selection ---
    selected_categories = select_categories(categories)
    if not selected_categories:
        console.print("[yellow]カテゴリが選択されていません。終了します。[/yellow]")
        sys.exit(0)

    selected_grades = select_grades()

    filtered = filter_events(events, selected_categories, selected_grades)
    console.print(f"\n[green]フィルタ後: {len(filtered)} 件[/green]")

    if not filtered:
        console.print("[yellow]条件に一致する行事がありません。[/yellow]")
        sys.exit(0)

    display_events_table(filtered, title="エクスポート対象イベント")

    # --- Output format ---
    fmt = select_output_format()
    output_dir = args.output_dir

    exported = []
    if fmt in ("ics", "both"):
        path = build_output_path(output_dir, "ics")
        export_ics(filtered, path)
        exported.append(path)

    if fmt in ("csv", "both"):
        path = build_output_path(output_dir, "csv")
        export_csv(filtered, path)
        exported.append(path)

    console.print("\n[bold green]エクスポート完了！[/bold green]")
    for p in exported:
        console.print(f"  → [underline]{p}[/underline]")


if __name__ == "__main__":
    main()
