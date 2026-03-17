"""Interactive CLI for category/grade selection and review step."""
from __future__ import annotations

import csv
import io
import os
import subprocess
import tempfile
from typing import Any

import questionary
from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


def display_events_table(events: list[dict], title: str = "解析結果") -> None:
    """Display extracted events in a rich table."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
    )
    table.add_column("No.", style="dim", width=4)
    table.add_column("日付", style="cyan", width=12)
    table.add_column("行事名", style="bold", width=24)
    table.add_column("カテゴリ", width=12)
    table.add_column("対象", width=8)
    table.add_column("開始", width=6)
    table.add_column("備考", width=20)

    for i, ev in enumerate(events, 1):
        table.add_row(
            str(i),
            ev.get("date") or "-",
            ev.get("title") or "-",
            ev.get("category") or "-",
            ev.get("target") or "-",
            ev.get("time_start") or "-",
            (ev.get("notes") or "")[:30],
        )

    console.print(table)
    console.print(f"[dim]合計 {len(events)} 件[/dim]\n")


def review_step(events: list[dict]) -> list[dict]:
    """Let the user review / edit events before export.

    Returns the (possibly modified) list of events.
    """
    display_events_table(events)

    choice = questionary.select(
        "解析結果を確認してください。",
        choices=[
            questionary.Choice("すべて承認して次へ進む", value="approve"),
            questionary.Choice("CSVで編集してから次へ進む", value="edit"),
            questionary.Choice("再解析する（このステップをスキップ）", value="retry"),
        ],
    ).ask()

    if choice == "approve":
        return events
    if choice == "retry":
        return []  # Signal to caller to re-run analysis
    if choice == "edit":
        return _edit_in_csv(events)
    return events


def _edit_in_csv(events: list[dict]) -> list[dict]:
    """Write events to a temp CSV, open in editor, read back."""
    fields = ["date", "title", "category", "target", "time_start", "time_end", "notes"]

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8-sig",
        newline="",
    ) as f:
        tmp_path = f.name
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)

    console.print(f"[yellow]一時CSVファイルを開きます: {tmp_path}[/yellow]")
    editor = os.environ.get("EDITOR", "nano")
    try:
        subprocess.run([editor, tmp_path], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            f"[red]エディタを起動できませんでした。手動で編集後 Enter を押してください: {tmp_path}[/red]"
        )
        input()

    edited: list[dict] = []
    with open(tmp_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {k: (v if v.strip() else None) for k, v in row.items()}
            edited.append(cleaned)

    os.unlink(tmp_path)
    console.print(f"[green]{len(edited)} 件のイベントを読み込みました。[/green]")
    return edited


def select_categories(categories: list[dict]) -> list[str]:
    """Checkbox selection for categories. Returns list of selected category IDs."""
    choices = [
        questionary.Choice(
            title=f"{c['name']}  [dim]{c['description']}[/dim]",
            value=c["id"],
            checked=True,
        )
        for c in categories
    ]
    selected = questionary.checkbox(
        "エクスポートするカテゴリを選択してください（スペースで選択/解除）:",
        choices=choices,
    ).ask()
    return selected or []


def select_grades() -> list[str]:
    """Checkbox selection for target grades."""
    choices = [
        questionary.Choice("全学年", value="全学年", checked=True),
        questionary.Choice("① (1年生)", value="①", checked=True),
        questionary.Choice("② (2年生)", value="②", checked=True),
        questionary.Choice("③ (3年生)", value="③", checked=True),
        questionary.Choice("対象不明 (null)", value="null", checked=True),
    ]
    selected = questionary.checkbox(
        "対象学年を選択してください:",
        choices=choices,
    ).ask()
    return selected or []


def filter_events(
    events: list[dict],
    selected_categories: list[str],
    selected_grades: list[str],
) -> list[dict]:
    """Filter events by selected categories and grades."""
    result = []
    for ev in events:
        if ev.get("category") not in selected_categories:
            continue
        target = ev.get("target")
        if target is None:
            if "null" not in selected_grades:
                continue
        elif not any(g in target for g in selected_grades if g != "null"):
            # Check if any selected grade string appears in the target field
            grade_match = False
            for g in selected_grades:
                if g == "null":
                    continue
                if g == "全学年" and ("全" in target or "全学年" in target):
                    grade_match = True
                    break
                if g in target:
                    grade_match = True
                    break
            if not grade_match:
                continue
        result.append(ev)
    return result


def select_output_format() -> str:
    """Let user choose export format."""
    return questionary.select(
        "出力形式を選択してください:",
        choices=[
            questionary.Choice("ICS（iCal形式・Googleカレンダー等）", value="ics"),
            questionary.Choice("CSV（Googleカレンダー用）", value="csv"),
            questionary.Choice("両方", value="both"),
        ],
    ).ask()
