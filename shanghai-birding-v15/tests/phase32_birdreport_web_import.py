from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'birdreport-web-exporter.user.js').read_text(encoding='utf8')
assert '@match        https://www.birdreport.cn/home/search/page.html*' in s
assert 'birdreport-7d-import-${data.observationWindow.end}.json' in s
assert '中文名' in s and '观测时间' in s and '观测地点' in s
assert '中国观鸟记录中心' in s
assert '其它观测记录' in s
print('PHASE 32 BIRDREPORT WEB EXPORTER PASS')
