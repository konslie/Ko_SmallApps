"""Serve only the bot's public gameplay status to a phone on the same LAN."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HTML = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sky Striker 진행 상황</title><style>body{background:#090d18;color:#e6edf7;font:18px system-ui;max-width:600px;margin:40px auto;padding:20px}h1{font-size:24px}#score{font-size:42px;color:#59ddff}pre{white-space:pre-wrap;line-height:1.8}small{color:#9daabd}</style><h1>Sky Striker</h1><div id="score">연결 중</div><pre id="info"></pre><small id="time"></small><script>
const names={falcon:'팔콘',raptor:'랩터',titan:'타이탄',phantom:'팬텀',wyvern:'와이번',nova:'노바',seraph:'세라프',origin:'오리진',spread:'산탄',homing:'유도탄',chain:'라이트닝',blade:'블레이드',vulcan:'벌컨',normal:'보통',hard:'어려움'};
async function update(){try{const s=await(await fetch('/status.json',{cache:'no-store'})).json(),p=s.player||{};document.querySelector('#score').textContent=Number(s.score||0).toLocaleString()+'점';document.querySelector('#info').textContent=(names[s.difficulty]||s.difficulty)+' · 스테이지 '+s.stage+'\n'+s.state+' / '+s.phase+'\n체력 '+p.hp+'/'+p.maxHp+' · 보호막 '+p.shield+'\n'+(names[p.aircraft]||p.aircraft)+' · '+(names[p.weapon]||p.weapon)+' Lv.'+p.weaponLevel+'\n격추 '+(s.stats?.kills||0)+' · 피격 '+(s.stats?.hits||0);const age=Math.round(Date.now()/1000-s.updatedAt);document.querySelector('#time').textContent=age>10?'갱신이 멈췄습니다 ('+age+'초 전)':'최근 갱신 '+new Date(s.updatedAt*1000).toLocaleTimeString();}catch{document.querySelector('#time').textContent='진행 기록을 기다리는 중';}}update();setInterval(update,2000);
</script></html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--status', default='status.json')
    args = parser.parse_args()
    status = Path(args.status)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                body, kind = HTML.encode(), 'text/html; charset=utf-8'
            elif self.path.split('?')[0] == '/status.json' and status.exists():
                body, kind = status.read_bytes(), 'application/json; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    print('진행 상황 서버 포트', args.port, flush=True)
    ThreadingHTTPServer(('0.0.0.0', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
