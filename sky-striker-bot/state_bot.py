"""Sky Striker controller using a read-only snapshot of the running game."""
import argparse
import getpass
import json
import math
import os
import re
import sys
import subprocess
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
      type:o.type, hp:o.hp, maxHp:o.maxHp, active:o.active, seek:!!o.seek,
      burst:!!o.burst, isBoss:!!o.isBoss, isPlanet:!!o.isPlanet, enterY:o.enterY,
      score:o.score || 0, speed:o.speed || 0,
      fireIn:o.fireInterval ? Math.max(0,o.fireInterval-o.fireTimer) : null});
    return {state:game.state, stage:game.stage, phase:game.phase, score:game.score,
      width:game.W, height:game.H, cardPick:game.cardPick,
      multiplier:game.multiplier, multiplierTimer:game.multiplierTimer,
      difficulty:game.difficulty,victory:document.getElementById('gameover-title').textContent === 'ALL CLEAR!',
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
        abilityCd:p.abilityCd,bombs:p.bombs,decay:p.decay,
        weaponCap:weaponCap(game.stage, game.difficulty)} : null,
      enemies:game.enemies.filter(e=>e.active).map(copy),
      bullets:game.enemyBullets.filter(e=>e.active).map(copy),
      beams:game.beams.filter(b=>b.owner && b.owner.active).map(b=>({
        x:b.owner.x,y:b.owner.y+b.owner.h*.3,angle:b.angle,width:b.width,
        t:b.t,warn:b.warn,fire:b.fire,vx:b.owner.vx || 0,vy:b.owner.vy || 0})),
      items:game.items.filter(e=>e.active).map(copy)};
  }});
"""


def choose_card(cards, player):
    def find(card_id):
        return next((i for i, card in enumerate(cards) if card['id'] == card_id), None)
    # PW x2 also stops the weapon level from decaying, which cost whole
    # bonus stages; while the weapon is below its cap it beats the score card.
    below_cap = player['weaponLevel'] < (player.get('weaponCap') or 8)
    if below_cap and find('pw2') is not None:
        return find('pw2')
    for i, card in enumerate(cards):
        if card["id"] == "score" or re.search(r"점수\s*[×x]\s*1\.5", card["desc"]):
            return i
    # Seraph's ultimate turns bullets into points and grants invulnerability.
    if player['aircraft'] == 'seraph' and find('ult') is not None:
        return find('ult')
    if find('pw2') is not None:
        return find('pw2')
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


def lightning_fallback(state):
    """Choose a temporary weapon when lightning cannot reach the boss."""
    p = state['player']
    if 'chain' not in state['unlockedWeapons']:
        return None
    if invulnerability_frames(p) > 48:
        return None
    # No blade fallback at low HP: a point-blank weapon on a damaged ship
    # cut damage in the late stages (33 switches in one run).
    visible = [e for e in state['enemies']
               if e['y'] > -e['h']/2 and e['y'] < state['height']]
    # fireChain measures the distance to the edge of the target.
    nearest = min((max(0, math.hypot(e['x']-p['x'], e['y']-(p['y']-p['h']/2))
                       - max(e['w'],e['h'])/2) for e in visible), default=None)
    lightning_range = state.get('lightningRange', 195)
    # Lightning deals nothing outside its range, while homing missiles reach
    # any distance. Switch on range alone; a wider band avoids flip-flopping.
    limit = lightning_range * (.85 if p['weapon'] == 'homing' else 1.05)
    # Only in boss fights: wave enemies come into range on their own, and with
    # many of them lightning's split strands far outdamage homing missiles.
    if (state['phase'] in ('midboss', 'boss') and nearest is not None and nearest > limit
            and 'homing' in state['unlockedWeapons']):
        return 'homing'
    return None


def switch_weapon(page, key):
    return switch_chip(page, 'weapon', key)


def switch_aircraft(page, key):
    return switch_chip(page, 'aircraft', key)


def switch_chip(page, kind, key):
    page.keyboard.press('Escape')
    panel = page.locator('#pause-screen')
    panel.wait_for(state='visible', timeout=3000)
    button = page.locator('#pause-' + kind + ' [data-' + kind + '="' + key + '"]:not([data-why])')
    if not button.count():
        page.locator('#resume-btn').click()
        return False
    button.click()
    page.keyboard.press('Escape')
    selected = 'active' in (button.get_attribute('class') or '').split()
    page.locator('#resume-btn').click()
    return selected


# Skill chain: effect timers belong to the player, not the aircraft, so they
# survive a swap. Nova's surge (6 s, damage x1.5, fire x2) is followed by
# seraph's sanctuary (5 s) and origin's big bang (3 s), all invulnerable.
# Ultimate charges and the ability cooldown are shared by every aircraft.
CHAIN = [('surge', 'nova', 'Space'), ('sanctuary', 'seraph', 'b'), ('bigbang', 'origin', 'b')]


def next_chain_step(s, step):
    """Next skill-chain move as (step, aircraft, key), or None to wait.

    step is the step in progress (None when idle); ('end', None, None) means
    return to the aircraft held before the chain.
    """
    p = s['player']
    unlocked = s['unlockedAircraft']
    in_fight = s['phase'] in ('midboss', 'boss')
    arrived = any(e['isBoss'] for e in s['enemies']) and not entering_bosses(s)
    if step is None:
        if (in_fight and arrived and 'nova' in unlocked and 'seraph' in unlocked
                and not p['abilityCd'] and p['bombs'] >= 1 and invulnerability_frames(p) < 30):
            return CHAIN[0]
        return None
    if not in_fight:
        return ('end', None, None)
    if step == 'surge' and (p.get('surge') or 0) <= 30:
        return CHAIN[1] if p['bombs'] >= 1 else ('end', None, None)
    if step == 'sanctuary' and (p.get('sanctuary') or 0) <= 20:
        return CHAIN[2] if 'origin' in unlocked and p['bombs'] >= 1 else ('end', None, None)
    if step == 'bigbang' and invulnerability_frames(p) == 0:
        return ('end', None, None)
    return None


def invulnerability_frames(player):
    return max(player.get(key, 0) or 0
               for key in ('invincible', 'star', 'surge', 'sanctuary', 'dash'))


# A shield layer absorbs one hit and then grants 60 invulnerable frames.
SHIELD_FRAMES = 60


def protection_budget(player):
    """Frames the ship can press forward, counting each shield as one hit."""
    return invulnerability_frames(player) + SHIELD_FRAMES * (player.get('shield') or 0)


def next_difficulty(difficulty, victory):
    if not victory:
        return None
    return {'normal': 'hard', 'hard': 'hell'}.get(difficulty)


class Telemetry:
    """Measured play data for comparing strategies, saved as JSON.

    weaponDps: boss HP lost per second while each weapon was held, split into
    'entry' (boss still descending, cannot fire) and 'fight' (boss attacking).
    """

    def __init__(self, path):
        self.path = Path(path)
        self.data = {'weaponDps': {}, 'bossFights': [], 'bonus': [], 'stages': [], 'levelDrops': []}
        self.last = None
        self.stage = None
        self.stage_time = self.x8_time = 0.0
        self.level = None
        self.fight = None
        self.boss_hp = None
        self.bonus = None

    def update(self, s, now):
        p = s['player']
        dt = 0.0 if self.last is None else min(.2, now - self.last)
        self.last = now
        if s['state'] != 'playing' or s['cardPick']:
            return   # The game clock stops here.
        x8 = (s.get('multiplier') or 1) >= 8
        if s['stage'] != self.stage:
            if self.stage is not None and self.stage_time:
                share = round(self.x8_time / self.stage_time, 3)
                self.data['stages'].append({'stage': self.stage, 'x8Share': share})
                print('기록 스테이지', self.stage, 'x8 유지', f'{share:.0%}', flush=True)
            self.stage, self.stage_time, self.x8_time = s['stage'], 0.0, 0.0
        self.stage_time += dt
        self.x8_time += dt if x8 else 0.0
        if self.level is not None and p['weaponLevel'] < self.level:
            self.data['levelDrops'].append({'stage': s['stage'], 'phase': s['phase'],
                                            'from': self.level, 'to': p['weaponLevel']})
            print('기록 무기 레벨 하락', self.level, '→', p['weaponLevel'], s['phase'], flush=True)
        self.level = p['weaponLevel']
        self._boss(s, p, now, dt)
        self._bonus(s, dt, x8)

    def _boss(self, s, p, now, dt):
        phase = s['phase']
        bosses = [e for e in s['enemies'] if e['isBoss']]
        if phase in ('midboss', 'boss'):
            if self.fight is None or self.fight['phase'] != phase:
                self.fight = {'stage': s['stage'], 'phase': phase, 'start': now, 'arrivedAt': None}
                self.boss_hp = None
            entering = any(e['y'] < e['enterY'] for e in bosses if e.get('enterY') is not None)
            if bosses and not entering and self.fight['arrivedAt'] is None:
                self.fight['arrivedAt'] = now
            total = sum(e['hp'] for e in bosses)
            # A new twin appearing raises the total; only count decreases.
            if bosses and self.boss_hp is not None and total <= self.boss_hp:
                key = p['weapon'] + (':entry' if entering else ':fight')
                w = self.data['weaponDps'].setdefault(key, {'damage': 0.0, 'seconds': 0.0})
                w['damage'] += self.boss_hp - total
                w['seconds'] += dt
            self.boss_hp = total if bosses else None
        elif self.fight is not None:
            f = self.fight
            arrived = f['arrivedAt']
            result = {'stage': f['stage'], 'phase': f['phase'],
                      'seconds': round(now - f['start'], 1),
                      'killedBeforeArrival': arrived is None,
                      'secondsAfterArrival': None if arrived is None else round(now - arrived, 1)}
            self.data['bossFights'].append(result)
            print('기록 보스전', f['phase'], '등장 중 처치' if arrived is None
                  else f'도착 후 {result["secondsAfterArrival"]}초', f'(총 {result["seconds"]}초)', flush=True)
            self.fight = self.boss_hp = None

    def _bonus(self, s, dt, x8):
        if s['phase'] == 'bonus':
            if self.bonus is None:
                self.bonus = {'stage': s['stage'], 'score': s['score'],
                              'kills': s['stats']['kills'], 'time': 0.0, 'x8': 0.0}
            self.bonus['time'] += dt
            self.bonus['x8'] += dt if x8 else 0.0
        elif self.bonus is not None:
            b = self.bonus
            result = {'stage': b['stage'], 'score': s['score'] - b['score'],
                      'kills': s['stats']['kills'] - b['kills'],
                      'x8Share': round(b['x8'] / b['time'], 3) if b['time'] else 0}
            self.data['bonus'].append(result)
            print('기록 보너스', result['stage'], '점수', result['score'], '격추', result['kills'],
                  'x8 유지', f"{result['x8Share']:.0%}", flush=True)
            self.bonus = None

    def save(self):
        out = dict(self.data)
        out['weaponDps'] = {k: {**v, 'dps': round(v['damage'] / v['seconds'], 1) if v['seconds'] else 0}
                            for k, v in self.data['weaponDps'].items()}
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
        temp.replace(self.path)


def entering_bosses(state):
    """Bosses still descending: they cannot fire yet but can be damaged."""
    return [e for e in state['enemies'] if e['isBoss']
            and e.get('enterY') is not None and e['y'] < e['enterY']]


def arrival_frames(boss):
    return (boss['enterY'] - boss['y']) / max(.1, boss['speed'])


def choose_move(state):
    p = state["player"]
    x, y = p["x"], p["y"]
    speed = p["speed"] * (0.55 if p["slowT"] else 1)
    immunity = invulnerability_frames(p)
    budget = protection_budget(p)
    retreat_y = state['height'] * .78
    escape_frames = max(0, retreat_y-y) / max(1, speed)
    # With a shield left, the next hit only costs that shield.
    expiring = not p['shield'] and 0 < immunity <= escape_frames + 24
    bullets = [b for b in state["bullets"] if -80 < b["y"] < state["height"]+80
               and abs(b["x"]-x) < 220 and abs(b["y"]-y) < 280]
    enemies = [e for e in state["enemies"] if -50 < e["y"] < state["height"]+50]
    targets = [e for e in enemies if e["y"] < y-30]
    entering_boss = next(iter(entering_bosses(state)), None)
    # A planet that passes the ship is lost with its points and its guaranteed
    # drop, while a boss waits until it is killed: planets outrank the boss.
    target = min(targets, key=lambda e: abs(e["x"]-x)*.25 - e["y"]*.55
                 - (150 if e["isBoss"] else 0)
                 - (max(0, 60-e['fireIn']) if p['weapon'] == 'chain'
                    and e.get('fireIn') is not None and not e.get('isPlanet') else 0)
                 - (250 + min(250, e.get("score", 0)/12) if e.get("isPlanet") else 0), default=None)
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
                # Every point is multiplied by the x2 item (up to x8), so it
                # comes first. HP rises to the top only when it is running out.
                kind = candidate.get('type')
                # The weapon loses a level after 40 s (2400 frames) without PW,
                # and a weak weapon misses planets and bosses alike.
                weapon_needs_pw = (p['weaponLevel'] < (p.get('weaponCap') or 8)
                                   or (p.get('decay') or 2400) < 600)
                if kind == 'hp' and p['hp'] <= max(2, p['maxHp'] / 3):
                    priority = 0
                elif kind == 'power' and weapon_needs_pw:
                    priority = 0
                else:
                    # Overdrive (fire rate x2, 8 s) and star (invulnerable, 6 s)
                    # are the main damage boosts, so they rank with the x2 item.
                    priority = {'multiplier': 0, 'star': 0, 'overdrive': 0,
                                'shield': 1, 'hp': 1, 'power': 1}.get(kind, 4)
                reachable_items.append((priority, remaining, t, candidate, intercept_y))
                break
    intercept = min(reachable_items, key=lambda v: (v[0], v[1], v[2]), default=None)
    # Keep shooting a planet that is close to passing the ship, unless it has
    # already passed. Reachable items remain the next priority.
    urgent_planet = bool(target and target.get('isPlanet') and target['y'] > y-200)
    boss_setup = state['phase'] in ('midwarn', 'bosswarn') or entering_boss is not None
    # A planet will not come back, the descending boss will: shoot the planet.
    planet_target = bool(target and target.get('isPlanet'))
    close_attack = boss_setup and p['weapon'] in ('spread', 'chain') and not planet_target
    # A boss fires as soon as it reaches enterY (its fire timer runs during the
    # descent), so leave the point-blank spot shortly before it arrives.
    nuke_exit = (entering_boss is not None and arrival_frames(entering_boss) <= 30
                 and budget <= 60)
    dogfight = bool(target and budget > escape_frames + 48 and not boss_setup
                    and state['phase'] in ('wave1', 'wave2', 'midboss', 'boss'))
    # Priority 0 items (x2, overdrive, star, needed PW/HP) are always worth the
    # detour. PW/shield/HP otherwise give 500 points times the multiplier, worth
    # it only when they are reachable within 45 frames.
    pursue_mult = (intercept is not None and not close_attack and not urgent_planet
                   and (intercept[0] == 0 or (intercept[0] == 1 and intercept[2] <= 45)))
    # Bonus stages have no enemy fire: only planet bodies hurt, and every planet
    # scores double. Trade HP for planets unless one more hit could be fatal.
    bonus_push = state['phase'] == 'bonus' and (p['hp'] > 2 or p['shield'] or immunity)
    pursue_item = intercept is not None and not urgent_planet and not close_attack and rescue is None
    if expiring or nuke_exit:
        # Leave the front before protection ends. Future hazard checks below
        # still account for beams and bullets after their immunity deadline.
        target_x, target_y = x, retreat_y
        pursue_item = False
    elif pursue_mult:
        _, _, _, item, intercept_y = intercept
        target_x, target_y = item["x"], intercept_y
        pursue_item = True
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
        boss_h = entering_boss['h'] if entering_boss else 70
        # Follow the descending boss instead of waiting at its arrival point:
        # the spread fan covers the whole 80px body only within about 70px.
        # Bosses spawn at y=-80, so wait near the top during the warning.
        boss_y = entering_boss['y'] if entering_boss else -80
        gap = 45 if p['weapon'] == 'spread' else 30
        # The boss body can damage the player during entry even before it fires.
        target_y = min(state['height']-p['h']/2,
                       max(p['h']/2, boss_y + (boss_h+p['h'])/2 + gap))
    elif pursue_item:
        _, _, _, item, intercept_y = intercept
        target_x, target_y = item["x"], intercept_y
    else:
        # Lead moving enemies by the expected player bullet travel time.
        flight = max(0, min(60, (y-target["y"])/10)) if target else 0
        target_x = max(15, min(state["width"]-15,
                       target["x"] + target["vx"] * flight)) if target else state["width"]/2
        target_y = state["height"]*.78
        if bonus_push and target:
            # Meet planets higher up to get more firing time before they pass.
            target_y = state['height']*.55
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
            objective += abs(goal_y-target_y)*(.8 if expiring or nuke_exit or dogfight or rescue or close_attack or bonus_push else .65 if pursue_item else .8 if target and p['weapon'] == 'chain' else .15)
            # Urgent collision avoidance dominates, but distant bullets should
            # not continuously pull the ship out of the firing line.
            # Pressing forward on a shield accepts a hit: it costs the shield
            # and kills shooters before they fire, and their drops refill it.
            hit_cost = (.3 if bonus_push else
                        .5 if dogfight and p['shield'] and not immunity else 1)
            score = max(0, danger-5)*10*hit_cost + objective + (2 if dx or dy else 0)
            if score < best_score:
                best,best_score,best_danger = (dx,dy),score,danger
    return best,best_danger


def read_env_file(path):
    values = {}
    if path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('"\'')
    return values


def load_credentials():
    """Nickname and PIN from the environment or .env, else asked at run time."""
    file_values = read_env_file(Path(__file__).with_name('.env'))
    lookup = lambda key: os.environ.get(key) or file_values.get(key) or ''
    nickname = lookup('SKY_NICK') or input('닉네임: ').strip()
    pin = lookup('SKY_PIN') or getpass.getpass('PIN: ')
    return nickname, pin


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
        for attempt in range(3):
            try:
                page.goto(URL, wait_until="domcontentloaded")
                break
            except Exception as error:
                # The tailnet address occasionally aborts the first request.
                if attempt == 2:
                    raise
                print('페이지 열기 실패, 다시 시도:', str(error).splitlines()[0], flush=True)
                page.wait_for_timeout(2000)
        if args.login:
            nickname, pin = load_credentials()
            page.locator('#settings-btn').wait_for(state='visible', timeout=15000)
            page.locator('#settings-btn').click()
            page.locator('#acc-nick').fill(nickname)
            page.locator('#acc-pin').fill(pin)
            pin = None
            page.locator('#acc-login button[type="submit"], #acc-login button:not([type])').click()
            # The form replaces itself with either the account row or a message.
            page.locator('#acc-logout, #acc-login ~ .acc-msg').first.wait_for(
                state='visible', timeout=15000)
            if not page.locator('#acc-logout').is_visible():
                message = page.locator('.acc-msg').inner_text()
                browser.close()
                raise SystemExit('로그인 실패: ' + message)
            message = page.locator('.acc-msg').inner_text() if page.locator('.acc-msg').count() else ''
            if '등록 완료' in message:
                # The server registers an unknown nickname instead of rejecting it.
                print('주의: 새 닉네임으로 등록되었습니다. 닉네임 오타를 확인하세요.', flush=True)
            print('로그인 확인:',page.locator('.acc-name').inner_text(),flush=True)
            page.locator('#settings-close').click()
        elif args.manual_login:
            # The person logs in themselves in the opened window; the bot
            # never sees the PIN and starts once the account is set.
            page.locator('#settings-btn').wait_for(state='visible', timeout=15000)
            page.locator('#settings-btn').click()
            print('열린 창에서 닉네임·PIN으로 로그인하세요. 로그인할 때까지 기다립니다.', flush=True)
            page.wait_for_function(
                "() => localStorage.getItem('skyStrikerAccount') && document.querySelector('#acc-logout')",
                timeout=0, polling=500)
            print('로그인 확인:', page.locator('.acc-name').inner_text(), flush=True)
            if page.locator('#settings-close').is_visible():
                page.locator('#settings-close').click()
        page.locator('[data-diff="normal"]').click()
        if args.resume:
            try:
                page.locator('#continue-btn').wait_for(state='visible', timeout=8000)
            except Exception:
                print('서버에서 이어하기 기록을 찾지 못했습니다. 새 게임은 시작하지 않습니다.', flush=True)
                page.screenshot(path=args.capture)
                browser.close()
                return
            page.locator('#continue-btn').click()
        else:
            page.locator("#start-btn").click()
        held = set()
        start = time.monotonic()
        last_stage = 0
        last_special = 0.0
        last_card = None
        last_phase = None
        previous_weapon = None
        boss_previous_weapon = None
        fallback_since = None
        recovery_since = None
        weapon_changed_at = 0.0
        status_at = 0.0
        completed = False
        tele = None   # one telemetry file per difficulty
        chain_step = chain_home = None   # skill chain in progress, aircraft to return to
        chain_retry_at = 0.0             # after a refused swap, wait before retrying
        def change_weapon(key):
            for held_key in held:
                page.keyboard.up(held_key)
            held.clear()
            return switch_weapon(page, key)
        def change_aircraft(key):
            for held_key in held:
                page.keyboard.up(held_key)
            held.clear()
            return switch_aircraft(page, key)
        while args.seconds <= 0 or time.monotonic()-start < args.seconds:
            s = page.evaluate("() => window.__pilotSnapshot()")
            p = s["player"]
            if time.monotonic() - status_at >= 2:
                status = {key:s.get(key) for key in ('state','stage','phase','score','difficulty','stats')}
                status['player'] = {key:p.get(key) for key in ('hp','maxHp','shield','aircraft','weapon','weaponLevel')} if p else None
                status['updatedAt'] = time.time()
                temp = Path(args.status).with_suffix('.tmp')
                temp.write_text(json.dumps(status,ensure_ascii=False),encoding='utf-8')
                temp.replace(args.status)
                status_at = time.monotonic()
                if tele:
                    tele.save()
            if s["state"] in ("gameover","credits"):
                print("최종",s["stage"],"스테이지",s["score"],"점",s["stats"],flush=True)
                if tele:
                    tele.save()
                    print('기록 저장', tele.path, flush=True)
                    tele = None
                # gameOver submits the score asynchronously. Keep the browser
                # alive until the server response arrives or the request times out.
                deadline = time.monotonic() + 10
                while not score_response and time.monotonic() < deadline:
                    page.wait_for_timeout(100)
                print('랭킹 제출',score_response[-1] if score_response else '응답 확인 실패',flush=True)
                status.update({key:s.get(key) for key in ('state','stage','phase','score','difficulty','stats')})
                status['updatedAt'] = time.time()
                status['ranking'] = score_response[-1] if score_response else None
                temp = Path(args.status).with_suffix('.tmp')
                temp.write_text(json.dumps(status,ensure_ascii=False),encoding='utf-8')
                temp.replace(args.status)
                page.screenshot(path=str(Path(args.capture).with_stem(Path(args.capture).stem+'-'+s['difficulty'])))
                upcoming = next_difficulty(s['difficulty'],s['victory']) if args.campaign else None
                if upcoming:
                    for key in held:
                        page.keyboard.up(key)
                    held.clear()
                    if s['state'] == 'credits':
                        page.keyboard.press('Escape')
                    page.locator('#gameover-menu-btn').click()
                    page.locator('[data-diff="'+upcoming+'"]').click()
                    score_response.clear()
                    page.locator('#start-btn').click()
                    page.wait_for_timeout(500)
                    started = page.evaluate("() => window.__pilotSnapshot().difficulty")
                    if started != upcoming:
                        # A locked difficulty falls back to normal; do not replay it.
                        print(upcoming, '난이도를 시작하지 못했습니다(잠김). 종료합니다.', flush=True)
                        completed = True
                        break
                    last_stage, last_phase, last_card = 0, None, None
                    previous_weapon = boss_previous_weapon = None
                    fallback_since = recovery_since = None
                    weapon_changed_at = last_special = 0.0
                    chain_step = chain_home = None
                    print(s['difficulty'], 'ALL CLEAR,', upcoming, '시작 — 시간 제한 없음', flush=True)
                    continue
                if s['state'] == 'credits':
                    page.keyboard.press('Escape')
                completed = True
                break
            if not p:
                page.wait_for_timeout(50)
                continue
            if tele is None:
                path = Path(args.telemetry)
                tele = Telemetry(path.with_stem(path.stem + '-' + s['difficulty']))
            tele.update(s, time.monotonic())
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
                    # Weapon for after the boss arrives: lightning in range
                    # (homing beyond it, see lightning_fallback), else homing.
                    boss_previous_weapon = next((key for key in ('chain', 'homing')
                                                 if key in s['unlockedWeapons']), p['weapon'])
                    # A descending boss cannot fire yet: nuke it point-blank with spread.
                    boss_weapon = 'spread'
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
                        # Seraph first: its ultimate turns nearby enemy bullets into points.
                        # Raptor (HP -1) is never worth leaving falcon for.
                        wanted = ["seraph","origin","nova","titan","wyvern","phantom","falcon"]
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
            boss_attacking = any(e['isBoss'] and e.get('enterY') is not None
                                 and e['y'] >= e['enterY'] for e in s['enemies'])
            in_boss_fight = s['phase'] in ('midboss', 'boss')
            move = (next_chain_step(s, chain_step)
                    if chain_step or time.monotonic() >= chain_retry_at else None)
            if move:
                step, aircraft, key = move
                if step != 'end':
                    if chain_step is None:
                        chain_home = p['aircraft']
                    if p['aircraft'] == aircraft or change_aircraft(aircraft):
                        page.keyboard.press(key)
                        print('스킬 연계', step, aircraft, flush=True)
                        chain_step = step
                        continue
                    print('스킬 연계 교체 실패', aircraft, flush=True)
                    chain_retry_at = time.monotonic() + 10
                # Chain over (or a swap refused, e.g. HP too low for that aircraft).
                if chain_home and p['aircraft'] != chain_home:
                    change_aircraft(chain_home)
                if chain_step is not None:
                    print('스킬 연계 종료', chain_home, flush=True)
                chain_step = chain_home = None
                if step == 'end':
                    continue
            # Spread is kept while a boss descends, and while protected in a boss
            # fight, since point-blank spread is the strongest burst.
            spread_window = in_boss_fight and p['weapon'] == 'spread' and (
                bool(entering_bosses(s)) or protection_budget(p) > 60)
            now = time.monotonic()
            # Only item and skill invulnerability (star, surge, sanctuary): the
            # frames after a hit (titan's 180) would pull a damaged ship to the boss.
            granted = max(p.get(key) or 0 for key in ('star', 'surge', 'sanctuary'))
            if (in_boss_fight and boss_attacking and granted > 150
                    and 'spread' in s['unlockedWeapons'] and p['weapon'] != 'spread'
                    and now-weapon_changed_at >= 2):
                weapon_changed_at = now
                if change_weapon('spread'):
                    print('무적 중 보스 근접, 산탄', flush=True)
                continue
            if (in_boss_fight and boss_attacking and p['weapon'] == 'spread'
                    and not spread_window and boss_previous_weapon
                    and boss_previous_weapon != 'spread' and now-weapon_changed_at >= .3):
                # The boss now fires. Pausing clears the game's held keys; the
                # controller's matching state is cleared in change_weapon.
                weapon_changed_at = now
                if change_weapon(boss_previous_weapon):
                    print('보스 도착, 주무기', boss_previous_weapon, flush=True)
                else:
                    print('보스 도착, 주무기 복구 실패', boss_previous_weapon, flush=True)
                continue
            if ('chain' in s['unlockedWeapons'] and not spread_window
                    and s['phase'] not in ('bonus', 'midwarn', 'bosswarn')):
                now = time.monotonic()
                fallback = lightning_fallback(s)
                if fallback:
                    recovery_since = None
                    if fallback_since is None:
                        fallback_since = now
                    if (p['weapon'] != fallback and now-fallback_since >= .5
                            and now-weapon_changed_at >= 2):
                        weapon_changed_at = time.monotonic()
                        if change_weapon(fallback):
                            print('사거리 밖/접근 위험, 임시 무기', fallback, flush=True)
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
                            print('사거리 안, 라이트닝 복귀', flush=True)
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
            elif (in_boss_fight and boss_attacking and p['bombs'] > 0
                    and invulnerability_frames(p) == 0 and time.monotonic()-last_special > 3):
                # Charges do not carry over to the next stage: spend them on a
                # dense barrage (seraph converts it to points) or to finish the boss.
                near = sum(1 for b in s['bullets']
                           if math.hypot(b['x']-p['x'], b['y']-p['y']) < 160)
                boss_low = any(e['isBoss'] and e.get('maxHp') and e['hp'] < e['maxHp'] * .25
                               for e in s['enemies'])
                if near >= 14 or boss_low:
                    page.keyboard.press("b")
                    last_special = time.monotonic()
            page.wait_for_timeout(35)
        else:
            print("시간 제한",flush=True)
        page.screenshot(path=args.capture)
        print("화면 저장",args.capture,flush=True)
        if args.sleep_when_done and completed:
            for key in held:
                page.keyboard.up(key)
            print('최종 게임 종료 확인, 맥북 잠자기 전환',flush=True)
            subprocess.run(['pmset','sleepnow'],check=True)
            # Keep the final result page open when the Mac wakes again.
            while not page.is_closed():
                page.wait_for_timeout(1000)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds",type=float,default=0,
                        help="실행 시간 제한(초), 기본 0은 게임이 끝날 때까지 실행")
    parser.add_argument("--headless",action="store_true")
    parser.add_argument('--browser', choices=('auto', 'chrome', 'chromium'), default='auto',
                        help='auto: macOS에서는 Chrome, 그 외에는 Playwright Chromium 사용')
    parser.add_argument("--login",action="store_true",help="로그인 정보를 안전하게 입력받아 게임 시작")
    parser.add_argument('--manual-login', action='store_true',
                        help='열린 브라우저 창에서 사람이 직접 로그인할 때까지 기다린 뒤 게임 시작')
    parser.add_argument('--resume', action='store_true', help='서버에서 불러온 이어하기 기록으로 재개')
    parser.add_argument('--campaign', action='store_true', help='보통부터 올클리어할 때마다 어려움, 지옥 순으로 이어서 진행')
    parser.add_argument('--sleep-when-done', action='store_true', help='최종 게임 종료 후 macOS 잠자기, 결과 화면 유지')
    parser.add_argument('--status', default='status.json', help='진행 상태 JSON 경로')
    parser.add_argument('--telemetry', default='telemetry.json',
                        help='측정 기록 JSON 경로 (난이도별로 -normal 등이 붙음)')
    parser.add_argument("--capture",default="state-result.png")
    args = parser.parse_args()
    if args.manual_login and (args.login or args.headless):
        parser.error('manual-login은 창을 띄워 직접 로그인하는 방식이라 --login, --headless와 함께 쓸 수 없습니다')
    if args.campaign and (args.seconds > 0 or args.resume):
        parser.error('campaign은 시간 제한 없이 보통 새 게임부터 시작합니다')
    if args.sleep_when_done and sys.platform != 'darwin':
        parser.error('잠자기 옵션은 macOS에서만 사용할 수 있습니다')
    run(args)
