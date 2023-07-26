import babi.highlight as H
import babi.user_data as UD
import json

pyshebang = '#!/usr/bin/env python3'

g = H.Grammars(UD.prefix_data('grammar_v1'), UD.xdg_data('grammar_v1'))

g_src_py = json.loads(g._scope_to_files["source.python"].read_bytes())
g_src_re_py = json.loads(g._scope_to_files["source.regexp.python"].read_bytes())
