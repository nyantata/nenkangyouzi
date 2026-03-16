"""Prompt templates for Claude API calls."""

SYSTEM_PROMPT = """\
あなたは学校の年間行事計画を解析する専門アシスタントです。
与えられたテキストから行事情報を正確に抽出してください。

【重要なルール】
1. 原文に存在する情報のみを抽出すること。推測・補完・創作は一切禁止。
2. 原文に記載がない項目は必ず null を返すこと。
3. 日付・時刻の形式が不明確な場合は、原文の表現をそのまま notes に記録すること。
4. 行事名は原文の表現を尊重すること。
"""

EXTRACTION_PROMPT_TEMPLATE = """\
以下の学校行事計画テキストから、すべての行事を抽出してJSONで返してください。

## カテゴリ定義
{categories_json}

## 抽出テキスト
{text}

## 出力形式
以下のJSONスキーマに厳密に従ってください。余分なテキストは一切出力せず、JSONのみを返してください。

```json
{{
  "events": [
    {{
      "date": "YYYY-MM-DD または null（原文に日付がある場合は必ず入力）",
      "title": "行事名（原文のまま）",
      "category": "カテゴリID（上記カテゴリ定義から選択）",
      "target": "対象学年（例: '全学年', '①', '②', '③', '①②', '①②③' 等）または null",
      "time_start": "HH:MM または null",
      "time_end": "HH:MM または null",
      "notes": "備考・詳細または null",
      "source_text": "原文の該当箇所（根拠となるテキスト）"
    }}
  ]
}}
```

## 注意事項
- date が読み取れない行事は date を null にして含めること
- 同一行事が複数学年に分かれている場合は別々のエントリとして抽出すること
- 年度が明記されていない場合は日付から年を推測せず null のままにすること
"""


def build_extraction_prompt(text: str, categories: list[dict]) -> str:
    import json
    categories_json = json.dumps(
        [{"id": c["id"], "name": c["name"], "description": c["description"]}
         for c in categories],
        ensure_ascii=False,
        indent=2,
    )
    return EXTRACTION_PROMPT_TEMPLATE.format(
        categories_json=categories_json,
        text=text,
    )
