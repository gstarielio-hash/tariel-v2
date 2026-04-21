from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "design_tokens" / "inspetor.tokens.json"
TARGET_PATH = PROJECT_ROOT / "static" / "css" / "inspetor" / "tokens.generated.css"


def _render_block(selector: str, values: dict[str, str]) -> str:
    lines = [f"{selector} {{"]
    for token_name, token_value in values.items():
        lines.append(f"  --{token_name}: {token_value};")
    lines.append("}")
    return "\n".join(lines)


def build_css(tokens_path: Path = SOURCE_PATH) -> str:
    payload = json.loads(tokens_path.read_text(encoding="utf-8"))
    light_tokens = payload["light"]
    dark_tokens = payload["dark"]

    sections = [
        "/* Auto-generated from design_tokens/inspetor.tokens.json by scripts/build_design_tokens.py. */",
        "/* Do not edit manually. */",
        _render_block(":root", light_tokens),
        _render_block('html[data-theme="dark"],\nbody[data-theme="dark"]', dark_tokens),
    ]
    return "\n\n".join(sections) + "\n"


def main() -> None:
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TARGET_PATH.write_text(build_css(), encoding="utf-8")
    print(f"Tokens gerados em {TARGET_PATH}")


if __name__ == "__main__":
    main()
