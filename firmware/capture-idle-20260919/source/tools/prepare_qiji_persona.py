"""Install the project's original persona as the official bootstrap default."""
from pathlib import Path
import json
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project/'tools/prepare_capture_idle.py'), str(root)], check=True)
persona = (project/'app/gemini_chat_minimal/SOUL.md').read_text()
if not 0 < len(persona.encode()) < 4000:
    raise RuntimeError('Persona must fit the 8192-byte shared system prompt')
p = root/'packages/ai_agent/src/core/memory_store.c'
s = p.read_text()
begin = '    /* Qiji original persona bootstrap */\n'
end = '    /* End Qiji persona bootstrap */\n'
if begin in s:
    a=s.index(begin);b=s.index(end,a)+len(end)
    block=s[a:b]
    fallback=block.split('#else\n',1)[1].split('#endif\n',1)[0]
else:
    a=s.index('    const char *default_soul =')
    b=s.index('    const char *default_user =',a)
    fallback=s[a:b]
literal='\n'.join('        '+json.dumps(line,ensure_ascii=False) for line in persona.splitlines(keepends=True))
replacement=begin+'#ifdef CONFIG_GEMINI_CHAT_MINIMAL\n    const char *default_soul =\n'+literal+';\n#else\n'+fallback+'#endif\n'+end+'\n'
p.write_text(s[:a]+replacement+s[b:])
print('Prepared original Qiji persona bootstrap; existing SOUL.md preserved')
