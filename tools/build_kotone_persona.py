"""Compile source-tagged character cards into the ai_agent's existing SOUL file."""
import argparse
import json
from pathlib import Path
import re

PROJECT = Path(__file__).resolve().parent.parent
APP = PROJECT / 'app/gemini_chat_minimal'


def compile_persona():
    sources = json.loads((APP / 'character/sources.json').read_text(encoding='utf-8'))
    knowledge = (APP / 'character/KNOWLEDGE.md').read_text(encoding='utf-8')
    tags = re.findall(r'\[([A-Z,]+)\]', knowledge)
    for tag in tags:
        for key in tag.split(','):
            if key not in sources['sources']:
                raise ValueError(f'Unknown character source: {key}')
    knowledge = re.sub(r'\[([A-Z,]+)\]', '', knowledge)
    behavior = (APP / 'character/BEHAVIOR.md').read_text(encoding='utf-8')
    persona = behavior.strip() + '\n\n' + knowledge.strip() + '\n'
    size = len(persona.encode('utf-8'))
    if not 0 < size < 4000:
        raise ValueError(f'Persona is {size} bytes; must remain below 4000 for shared 8192-byte context')
    return persona


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    persona = compile_persona()
    target = APP / 'SOUL.md'
    if args.check:
        if target.read_text(encoding='utf-8') != persona:
            raise SystemExit('SOUL.md is stale; run tools/build_kotone_persona.py')
    else:
        target.write_text(persona, encoding='utf-8', newline='\n')
    print(f'Kotone persona: {len(persona.encode("utf-8"))} bytes; sources validated')


if __name__ == '__main__':
    main()
