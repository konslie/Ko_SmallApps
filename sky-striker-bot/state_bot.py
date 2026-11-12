"""Sky Striker controller using a read-only snapshot of the running game."""
import argparse
import getpass
import math
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://jimmy.tail1e4df5.ts.net/"
MARKER = "  new Game();"
EXPOSURE = """
  const game = new Game();
  Object.defineProperty(window, '__pilotSnapshot', {value: () => {
    const p = game.player;
    const copy = o => ({x:o.x, y:o.y, vx:o.vx || 0, vy:o.vy || 0,
      w:o.w || (o.r ? o.r*2 : 28), h:o.h || (o.r ? o.r*2 : 28),
      type:o.type, hp:o.hp, active:o.active, seek:!!o.seek,
      burst:!!o.burst, isBoss:!!o.isBoss, isPlanet:!!o.isPlanet, enterY:o.enterY,
      score:o.score || 0, speed:o.speed || 0,
      fireIn:o.fireInterval ? Math.max(0,o.fireInterval-o.fireTimer) : null});
    return {state:game.state, stage:game.stage, phase:game.phase, score:game.score,
      width:game.W, height:game.H, cardPick:game.cardPick,
      cards:(game.cardChoices || []).map(c => ({id:c.id, name:c.name, desc:c.desc})),
      clearedStage:game.clearedStage,
      unlockedAircraft:Object.keys(AIRCRAFT).filter(k => game.isUnlocked(k)),
      unlockedWeapons:Object.keys(WEAPON_SYSTEMS).filter(k => game.isWeaponUnlocked(k)),
      lightningRange:p ? WEAPON_SYSTEMS.chain.levels[p.weaponLevel-1].range : 0,
      stats:game.stats ? {kills:game.stats.kills,hits:game.stats.hits,ults:game.stats.ults} : null,
      player:p ? {x:p.x,y:p.y,w:p.w,h:p.h,speed:p.speed,hp:p.hp,maxHp:p.maxHp,
        shield:p.shield,invincible:p.invincible,star:p.star,slowT:p.slowT,
        surge:p.surge,sanctuary:p.sanctuary,dash:p.dash,
        aircraft:p.aircraft,weapon:p.weaponSystem,weaponLevel:p.weaponLevel,
        weaponRange:WEAPON_SYSTEMS[p.weaponSystem].levels[p.weaponLevel-1].range || 0,
        abilityCd:p.abilityCd,bombs:p.bombs} : null,
      enemies:game.enemies.filter(e=>e.active).map(copy),
      bullets:game.enemyBullets.filter(e=>e.active).map(copy),
      beams:game.beams.filter(b=>b.owner && b.owner.active).map(b=>({
        x:b.owner.x,y:b.owner.y+b.owner.h*.3,angle:b.angle,width:b.width,
        t:b.t,warn:b.warn,fire:b.fire,vx:b.owner.vx || 0,vy:b.owner.vy || 0})),
      items:game.items.filter(e=>e.active).map(copy)};
  }});
"""


def choose_card(cards, player):
    for i, card in enumerate(cards):
        if card["id"] == "score" or re.search(r"점수\s*[×x]\s*1\.5", card["desc"]):
            return i
    if player['hp'] >= player['maxHp'] / 2:
        for i, card in enumerate(cards):
            if card['id'] == 'luck':
                return i
    def value(card):
        name = card["name"]
        if (card['id'] == 'heal' or '회복' in name or '수리' in name) and player["hp"] <= player["maxHp"] - 2:
            return 12
        return sum(weight for word, weight in
                   [("화력", 9), ("자석", 7), ("보호", 6), ("필살기", 5), ("연사", 5)]
                   if word in name)
    return max(range(len(cards)), key=lambda i: value(cards[i]))


def lightning_fallback(state, danger, direction):
    """Choose a temporary weapon when lightning cannot safely engage."""
    p = state['player']
    if 'chain' not in state['unlockedWeapons']:
        return None
    if invulnerability_frames(p) > 48:
        return None
    threats = [b for b in state['bullets']
               if abs(b['x']-p['x']) < 130 and abs(b['y']-p['y']) < 200]
    low_hp = p['hp'] < p['maxHp'] / 2
    if low_hp and 'blade' in state['unlockedWeapons'] and (danger >= 12 or len(threats) >= 3):
        return 'blade'
    visible = [e for e in state['enemies']
               if e['y'] > -e['h']/2 and e['y'] < state['height']]
    # fireChain measures the distance to the edge of the target.
    nearest = min((max(0, math.hypot(e['x']-p['x'], e['y']-(p['y']-p['h']/2))
                       - max(e['w'],e['h'])/2) for e in visible), default=None)
    lightning_range = state.get('lightningRange', 195)
    blocked = danger >= 12 or (len(threats) >= 3 and direction[1] >= 0)
    if (nearest is not None and nearest > lightning_range * 1.05 and blocked
            and 'homing' in state['unlockedWeapons']):
        return 'homing'
    return None


def switch_weapon(page, key):
    page.keyboard.press('Escape')
    panel = page.locator('#pause-screen')
    panel.wait_for(state='visible', timeout=3000)
    button = page.locator('#pause-weapon [data-weapon="' + key + '"]:not([data-why])')
    if not button.count():
        page.locator('#resume-btn').click()
        return False
    button.click()
    page.keyboard.press('Escape')
    selected = 'active' in (button.get_attribute('class') or '').split()
    page.locator('#resume-btn').click()
    return selected


def invulnerability_frames(player):
    return max(player.get(key, 0) or 0
               for key in ('invincible', 'star', 'surge', 'sanctuary', 'dash'))


def choose_move(state):
    p = state["player"]
    x, y = p["x"], p["y"]
    speed = p["speed"] * (0.55 if p["slowT"] else 1)
    immunity = invulnerability_frames(p)
    retreat_y = state['height'] * .78
    escape_frames = max(0, retreat_y-y) / max(1, speed)
    expiring = 0 < immunity <= escape_frames + 24
    bullets = [b for b in state["bullets"] if -80 < b["y"] < state["height"]+80
               and abs(b["x"]-x) < 220 and abs(b["y"]-y) < 280]
    enemies = [e for e in state["enemies"] if -50 < e["y"] < state["height"]+50]
    targets = [e for e in enemies if e["y"] < y-30]
    entering_boss = next((e for e in state['enemies'] if e['isBoss']
                          and e.get('enterY') is not None and e['y'] < e['enterY']), None)
    target = min(targets, key=lambda e: abs(e["x"]-x)*.25 - e["y"]*.55
                 - (150 if e["isBoss"] else 0)
                 - (max(0, 60-e['fireIn']) if p['weapon'] == 'chain'
                    and e.get('fireIn') is not None and not e.get('isPlanet') else 0)
                 - (min(120, e.get("score", 0)/20) if e.get("isPlanet") else 0), default=None)
    # When approaching a boss from below, prevent ordinary enemies from
    # slipping behind the ship. Only chase those we can get below in time.
    stragglers = []
    for enemy in enemies:
        if enemy['isBoss'] or enemy.get('isPlanet'):
            continue
        if enemy['y'] < y - 100:
            continue
        down_speed = max(0, enemy['vy'] or enemy['speed'])
        for t in range(0, 121, 5):
            enemy_y = enemy['y'] + down_speed * t
            firing_y = enemy_y + (enemy['h'] + p['h'])/2 + 15
            if firing_y >= state['height'] - p['h']/2:
                break
            firing_x = max(p['w']/2, min(state['width']-p['w']/2,
                           enemy['x'] + enemy['vx']*t))
            if max(abs(firing_x-x), abs(firing_y-y)) <= speed*t + 10:
                deadline = (state['height'] - enemy_y) / max(.5, down_speed)
                stragglers.append((deadline, t, firing_x, firing_y))
                break
    rescue = min(stragglers, key=lambda value: (value[0], value[1]), default=None)
    # Predict the first reachable intercept before the item leaves the screen.
    # The game moves items 1.5 logical pixels per frame. Movement is independent
    # on each axis, so reachability uses the slower of the two axes.
    reachable_items = []
    for candidate in state["items"]:
        if candidate["y"] > state["height"] + 14:
            continue
        remaining = (state["height"] + 14 - candidate["y"]) / 1.5
        for t in range(0, min(180, int(remaining)) + 1, 5):
            intercept_y = min(state["height"] - p["h"]/2, candidate["y"] + 1.5*t)
            if max(abs(candidate["x"]-x), abs(intercept_y-y)) <= speed*t + 18:
                priority = {'star': 0, 'power': 1, 'shield': 2,
                            'hp': 2, 'multiplier': 3, 'overdrive': 3}.get(candidate.get('type'), 4)
                reachable_items.append((priority, remaining, t, candidate, intercept_y))
                break
    intercept = min(reachable_items, key=lambda v: (v[0], v[1], v[2]), default=None)
    # Keep shooting a planet that is close to passing the ship, unless it has
    # already passed. Reachable items remain the next priority.
    urgent_planet = bool(target and target.get('isPlanet') and target['y'] > y-200)
    boss_setup = state['phase'] in ('midwarn', 'bosswarn') or entering_boss is not None
    close_attack = boss_setup and p['weapon'] in ('spread', 'chain')
    dogfight = bool(target and immunity > escape_frames + 48
                    and state['phase'] in ('wave1', 'wave2', 'midboss', 'boss'))
    pursue_item = intercept is not None and not urgent_planet and not close_attack and rescue is None
    if expiring:
        # Leave the front before protection ends. Future hazard checks below
        # still account for beams and bullets after their immunity deadline.
        target_x, target_y = x, retreat_y
        pursue_item = False
    elif dogfight:
        target_x = target['x']
        gap = (target['h'] + p['h'])/2 + 12
        if p['weapon'] == 'chain':
            gap = max(gap, p['weaponRange']*.55)
        target_y = min(state['height']-p['h']/2, target['y'] + gap)
        pursue_item = False
    elif rescue:
        _, _, target_x, target_y = rescue
    elif close_attack:
        # Spawn locations are centered for one boss and at the thirds for twins.
        target_x = entering_boss['x'] if entering_boss else state['width']/2
        boss_h = entering_boss['h'] if entering_boss else 80
        boss_y = max(entering_boss['y'], entering_boss['enterY']) if entering_boss else 100
        # The boss body can damage the player during entry even before it fires.
        target_y = min(state['height']-p['h']/2, boss_y + (boss_h+p['h'])/2 + 30)
    elif pursue_item:
        _, _, _, item, intercept_y = intercept
        target_x, target_y = item["x"], intercept_y
    else:
        # Lead moving enemies by the expected player bullet travel time.
        flight = max(0, min(60, (y-target["y"])/10)) if target else 0
        target_x = max(15, min(state["width"]-15,
                       target["x"] + target["vx"] * flight)) if target else state["width"]/2
        target_y = state["height"]*.78
        if target and p['weapon'] == 'chain':
            # Lightning originates at the ship and needs a target inside its
            # level-dependent range. Stay short of the edge of that range.
            target_y = min(state['height']-p['h']/2,
                           max(target['y'] + (target['h']+p['h'])/2 + 25,
                               target['y'] + p['weaponRange']*.65))
    best, best_score, best_danger = (0,0), float("inf"), float("inf")
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            danger = 0.0
            for t in (4,8,12,18,24,30):
                px = min(state["width"]-p["w"]/2,max(p["w"]/2,x+dx*speed*t))
                py = min(state["height"]-p["h"]/2,max(p["h"]/2,y+dy*speed*t))
                if immunity > t + 12:
                    continue
                for b in bullets:
                    bx, by = b["x"]+b["vx"]*t, b["y"]+b["vy"]*t
                    gapx = abs(px-bx)-(p["w"]+b["w"])/2
                    gapy = abs(py-by)-(p["h"]+b["h"])/2
                    margin = math.hypot(max(0,gapx),max(0,gapy))
                    risk = max(0,42-margin) * (1.0-t/50)
                    if b["seek"] or b["burst"]: risk *= 1.4
                    danger = max(danger,risk)
                for beam in state.get('beams', []):
                    # The warning ray follows its owner and becomes a damaging
                    # half-line after warn frames. Move clear during the warning.
                    if beam['t'] + t > beam['warn'] + beam['fire']:
                        continue
                    bx, by = beam['x']+beam['vx']*t, beam['y']+beam['vy']*t
                    ux, uy = math.cos(beam['angle']), math.sin(beam['angle'])
                    along = (px-bx)*ux + (py-by)*uy
                    perpendicular = abs((px-bx)*uy - (py-by)*ux)
                    clearance = beam['width']/2 + p['w']*.22 + 24
                    if along > 0 and perpendicular < clearance:
                        danger = max(danger, 70*(clearance-perpendicular)/clearance)
                for e in enemies:
                    ex = e["x"]+e["vx"]*t
                    ey = e["y"]+(e["vy"] or e["speed"])*t
                    gap = math.hypot(max(0,abs(px-ex)-(p["w"]+e["w"])/2),
                                     max(0,abs(py-ey)-(p["h"]+e["h"])/2))
                    danger = max(danger,max(0,35-gap)*(1.0-t/50))
            # The controller replans frequently, so judging the objective at
            # 30 frames would overshoot a nearby item and prefer standing still.
            travel = 8
            goal_x = min(state["width"]-p["w"]/2,max(p["w"]/2,x+dx*speed*travel))
            goal_y = min(state["height"]-p["h"]/2,max(p["h"]/2,y+dy*speed*travel))
            objective = abs(goal_x-target_x)*(0.8 if not pursue_item else 0.9)
            objective += abs(goal_y-target_y)*(.8 if expiring or dogfight or rescue or close_attack else .65 if pursue_item else .8 if target and p['weapon'] == 'chain' else .15)
            # Urgent collision avoidance dominates, but distant bullets should
            # not continuously pull the ship out of the firing line.
            score = max(0, danger-5)*10 + objective + (2 if dx or dy else 0)
            if score < best_score:
                best,best_score,best_danger = (dx,dy),score,danger
    return best,best_danger


def run(args):
    with sync_playwright() as pw:
        launch_options = {'headless': args.headless}
        if args.browser == 'chrome' or (args.browser == 'auto' and sys.platform == 'darwin'):
            launch_options['channel'] = 'chrome'
        browser = pw.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width":800,"height":900})
        def instrument(route):
            response = route.fetch()
            html = response.text()
            if html.count(MARKER) != 1:
                raise RuntimeError("Game 생성 지점을 찾을 수 없습니다. 사이트 코드 변경을 확인하세요.")
            route.fulfill(response=response, body=html.replace(MARKER,EXPOSURE,1))
        page.route(re.compile(r"^https://jimmy\.tail1e4df5\.ts\.net/?$"),instrument)
        score_response = []
        def record_score_response(response):
            if response.url.endswith('/api/score') and response.request.method == 'POST':
                try:
                    body = response.json()
                except Exception:
                    body = {}
                score_response.append({'status':response.status, 'rank':body.get('rank'),
                                       'error':body.get('error')})
        page.on('response', record_score_response)
        page.goto(URL, wait_until="domcontentloaded")
        if args.login:
            nickname = input('닉네임: ').strip()
            pin = getpass.getpass('PIN: ')
            page.locator('#settings-btn').wait_for(state='visible', timeout=15000)
            page.locator('#settings-btn').click()
            page.locator('#acc-nick').fill(nickname)
            page.locator('#acc-pin').fill(pin)
            pin = None
            page.locator('#acc-login button[type="submit"], #acc-login button:not([type])').click()
            page.locator('#acc-logout').wait_for(state='visible', timeout=15000)
            print('로그인 확인:',page.locator('.acc-name').inner_text(),flush=True)
            page.locator('#settings-close').click()
        page.locator('[data-diff="normal"]').click()
        page.locator("#start-btn").click()
        held = set()
        start = time.monotonic()
        last_stage = 0
        last_special = 0.0
        last_card = None
        last_phase = None
        previous_weapon = None
        boss_previous_weapon = None
        boss_retreat_switched = False
        fallback_since = None
        recovery_since = None
        weapon_changed_at = 0.0
        def change_weapon(key):
            for held_key in held:
                page.keyboard.up(held_key)
            held.clear()
            return switch_weapon(page, key)
        while time.monotonic()-start < args.seconds:
            s = page.evaluate("() => window.__pilotSnapshot()")
            p = s["player"]
            if s["state"] in ("gameover","credits"):
                print("최종",s["stage"],"스테이지",s["score"],"점",s["stats"],flush=True)
                # gameOver submits the score asynchronously. Keep the browser
                # alive until the server response arrives or the request times out.
                deadline = time.monotonic() + 10
                while not score_response and time.monotonic() < deadline:
                    page.wait_for_timeout(100)
                print('랭킹 제출',score_response[-1] if score_response else '응답 확인 실패',flush=True)
                break
            if not p:
                page.wait_for_timeout(50)
                continue
            if s['state'] == 'playing' and not s['cardPick'] and s['phase'] != last_phase:
                if s['phase'] == 'bonus':
                    previous_weapon = 'chain' if 'chain' in s['unlockedWeapons'] else p['weapon']
                    bonus_weapon = next((key for key in ('chain', 'spread')
                                         if key in s['unlockedWeapons']), None)
                    if bonus_weapon and bonus_weapon != p['weapon']:
                        print('보너스 무기',bonus_weapon,
                              '적용' if change_weapon(bonus_weapon) else '선택 실패',flush=True)
                elif last_phase == 'bonus' and previous_weapon:
                    if p['weapon'] != previous_weapon:
                        print('일반전 무기',previous_weapon,
                              '복구' if change_weapon(previous_weapon) else '복구 실패',flush=True)
                    previous_weapon = None
                if s['phase'] in ('midwarn', 'bosswarn') and 'spread' in s['unlockedWeapons']:
                    boss_previous_weapon = 'chain' if 'chain' in s['unlockedWeapons'] else p['weapon']
                    boss_retreat_switched = False
                    boss_weapon = 'chain' if 'chain' in s['unlockedWeapons'] else 'spread'
                    if p['weapon'] != boss_weapon:
                        print('보스전 무기', boss_weapon, '적용' if change_weapon(boss_weapon) else '선택 실패', flush=True)
                elif last_phase in ('midboss', 'boss') and s['phase'] not in ('midboss', 'boss'):
                    if boss_previous_weapon and boss_previous_weapon != p['weapon']:
                        print('일반전 무기', boss_previous_weapon,
                              '복구' if change_weapon(boss_previous_weapon) else '복구 실패', flush=True)
                    boss_previous_weapon = None
                last_phase = s['phase']
                continue
            if s["cardPick"] and s["cards"]:
                for key in held: page.keyboard.up(key)
                held.clear()
                choice = choose_card(s["cards"],p)
                print("보상",s["cards"][choice]["name"],flush=True)
                page.keyboard.press(str(choice+1))
                last_card = s["stage"]
                continue
            if s["stage"] != last_stage and s["state"] == "playing":
                last_stage = s["stage"]
                print("스테이지",last_stage,"점수",s["score"],"체력",p["hp"],
                      "격추",s["stats"]["kills"],flush=True)
                if last_card is not None:
                    # The pause menu displays only currently permitted equipment.
                    page.keyboard.press("p")
                    if page.locator("#pause-screen").is_visible():
                        aircraft = page.locator("#pause-aircraft button:not([data-why])")
                        wanted = ["origin","seraph","nova","wyvern","phantom","titan","raptor"]
                        chosen = next((v for v in wanted if v in s["unlockedAircraft"]
                                       and page.locator('#pause-aircraft [data-aircraft="'+v+'"]:not([data-why])').count()),None)
                        if chosen:
                            page.locator('#pause-aircraft [data-aircraft="'+chosen+'"]').click()
                            page.keyboard.press('Escape')
                        weapons = page.locator("#pause-weapon button:not([data-why])")
                        chosen = next((v for v in ["chain","homing","spread"]
                                       if v in s["unlockedWeapons"]
                                       and page.locator('#pause-weapon [data-weapon="'+v+'"]:not([data-why])').count()),None)
                        if chosen:
                            page.locator('#pause-weapon [data-weapon="'+chosen+'"]').click()
                            page.keyboard.press('Escape')
                        print("장비",page.locator("#pause-aircraft .active").inner_text(),
                              page.locator("#pause-weapon .active").inner_text(),flush=True)
                        page.locator("#resume-btn").click()
                    last_card = None
                    continue
            if s["state"] != "playing":
                page.wait_for_timeout(50)
                continue
            (dx,dy),danger = choose_move(s)
            if 'chain' in s['unlockedWeapons'] and s['phase'] not in ('bonus', 'midwarn', 'bosswarn'):
                now = time.monotonic()
                fallback = lightning_fallback(s, danger, (dx,dy))
                if fallback:
                    recovery_since = None
                    if fallback_since is None:
                        fallback_since = now
                    if (p['weapon'] != fallback and now-fallback_since >= .5
                            and now-weapon_changed_at >= 2):
                        weapon_changed_at = time.monotonic()
                        if change_weapon(fallback):
                            print('접근 위험, 임시 무기', fallback, flush=True)
                            boss_retreat_switched = True
                        continue
                else:
                    fallback_since = None
                    if danger > 10:
                        recovery_since = None
                    elif recovery_since is None:
                        recovery_since = now
                    if (p['weapon'] != 'chain' and recovery_since is not None
                            and now-recovery_since >= 1.5
                            and now-weapon_changed_at >= 2):
                        weapon_changed_at = time.monotonic()
                        if change_weapon('chain'):
                            print('위험 감소, 라이트닝 복귀', flush=True)
                        continue
            boss_attacking = any(e['isBoss'] and e.get('enterY') is not None
                                 and e['y'] >= e['enterY'] for e in s['enemies'])
            if (s['phase'] in ('midboss', 'boss') and boss_attacking and dy > 0
                    and not boss_retreat_switched and boss_previous_weapon):
                if p['weapon'] != boss_previous_weapon:
                    # Pausing clears the game's held keys. Clear the controller's
                    # matching state as well so movement resumes correctly.
                    if change_weapon(boss_previous_weapon):
                        print('보스 후퇴, 주무기 복구', boss_previous_weapon, flush=True)
                    else:
                        print('보스 후퇴, 주무기 복구 실패', boss_previous_weapon, flush=True)
                boss_retreat_switched = True
                continue
            keys=set()
            if dx: keys.add("ArrowRight" if dx>0 else "ArrowLeft")
            if dy: keys.add("ArrowDown" if dy>0 else "ArrowUp")
            for key in held-keys: page.keyboard.up(key)
            for key in keys-held: page.keyboard.down(key)
            held=keys
            if danger > 23 and invulnerability_frames(p) == 0 and time.monotonic()-last_special > 1:
                if p["aircraft"] in ("falcon", "phantom", "titan"):
                    # Their abilities are either passive or the same as the
                    # ultimate. Space cannot rescue them from imminent danger.
                    if p["bombs"] > 0: page.keyboard.press("b")
                else:
                    if p["abilityCd"] == 0: page.keyboard.press("Space")
                    elif p["bombs"] > 0 and danger > 30: page.keyboard.press("b")
                last_special = time.monotonic()
            page.wait_for_timeout(35)
        else:
            print("시간 제한",flush=True)
        page.screenshot(path=args.capture)
        print("화면 저장",args.capture,flush=True)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds",type=float,default=3600)
    parser.add_argument("--headless",action="store_true")
    parser.add_argument('--browser', choices=('auto', 'chrome', 'chromium'), default='auto',
                        help='auto: macOS에서는 Chrome, 그 외에는 Playwright Chromium 사용')
    parser.add_argument("--login",action="store_true",help="로그인 정보를 안전하게 입력받아 게임 시작")
    parser.add_argument("--capture",default="state-result.png")
    run(parser.parse_args())
