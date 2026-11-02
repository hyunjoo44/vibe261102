"""
Shooting.py - 종스크롤 슈팅 게임 "SKY STRIKE" (pygame)

조작:
  방향키 / WASD : 이동
  Z 또는 Space  : 기총 발사 (공중 적)
  X             : 폭탄 투하 (지상 적, 조준점 위치에 떨어짐)
  P             : 일시정지
  M             : 효과음 켜기/끄기
  Enter / R     : 시작 / 재시작
  ESC           : 종료

파워업 아이템(P)을 먹을 때마다 총알이 2 → 4 → 8 → 16발로 늘어난다.
격추되면 한 단계 내려간다. 최대 단계에서 먹으면 보너스 1000점.
"""
import math
import random
import sys
from array import array

import pygame

W, H = 480, 640
FPS = 60
TILE = 32
COLS = W // TILE
SCROLL_SPEED = 1.2
SIGHT_DIST = 150
POWER_SHOTS = (2, 4, 8, 16)          # 파워 단계별 총알 수
POWER_SPREAD = (0.0, 0.18, 0.45, 0.9)  # 단계별 부채꼴 반각(라디안)

# 색상
GRASS = (70, 120, 60)
GRASS2 = (60, 108, 52)
FOREST = (34, 80, 40)
FOREST_DARK = (24, 62, 30)
FOREST_LIGHT = (50, 100, 52)
WATER = (40, 90, 150)
WATER_LIGHT = (80, 140, 200)
SAND = (170, 150, 100)
ROAD = (105, 100, 92)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


# ---------------------------------------------------------------- 효과음
class Sfx:
    """효과음을 코드로 합성한다 (외부 파일 불필요). 오디오 장치가 없으면 무음으로 동작."""

    def __init__(self):
        self.sounds = {}
        self.muted = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, size, self.channels = pygame.mixer.get_init()
            if size != -16:
                return
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.shot_channel = pygame.mixer.Channel(0)
        except pygame.error:
            return

        tone, mix, seq = self._tone, self._mix, self._seq
        self.sounds = {
            "shot": self._make(tone(0.05, 1400, 700, 0.07, "square", 1.5)),
            "bomb": self._make(tone(0.35, 1500, 400, 0.12, "tri", 0.3)),
            "impact": self._make(tone(0.2, 0, 0, 0.3, "noise", 2.0, 0.75)),
            "boom": self._make(tone(0.3, 0, 0, 0.45, "noise", 2.0, 0.6)),
            "boom_big": self._make(mix(tone(0.9, 0, 0, 0.7, "noise", 1.5, 0.85),
                                       tone(0.9, 120, 40, 0.3, "square", 2.0))),
            "clang": self._make(tone(0.08, 320, 260, 0.2, "square", 2.0)),
            "die": self._make(mix(tone(1.0, 0, 0, 0.6, "noise", 1.2, 0.8),
                                  tone(1.0, 600, 60, 0.25, "square", 1.0))),
            "powerup": self._make(seq([523, 659, 784, 1047], 0.07, 0.15, "square")),
            "bonus": self._make(seq([1047, 1319, 1568], 0.06, 0.15, "square")),
            "start": self._make(seq([392, 523, 659, 784], 0.1, 0.25, "tri")),
            "gameover": self._make(seq([523, 392, 330, 262], 0.18, 0.25, "tri")),
        }

    def _tone(self, dur, f0, f1, vol, wave="square", decay=1.0, smooth=0.0):
        n = int(self.rate * dur)
        out = []
        phase = noise = 0.0
        gain = math.sqrt((1 + smooth) / (1 - smooth)) * 1.7
        for i in range(n):
            t = i / n
            phase += (f0 + (f1 - f0) * t) / self.rate
            if wave == "square":
                v = 1.0 if phase % 1 < 0.5 else -1.0
            elif wave == "tri":
                v = 4 * abs(phase % 1 - 0.5) - 1
            else:  # 저역 통과한 노이즈 (폭발음)
                noise = noise * smooth + random.uniform(-1, 1) * (1 - smooth)
                v = noise * gain
            out.append(v * vol * (1 - t) ** decay)
        return out

    def _seq(self, notes, dur, vol, wave):
        out = []
        for f in notes:
            out += self._tone(dur, f, f, vol, wave, 0.5)
        return out

    @staticmethod
    def _mix(a, b):
        return [x + y for x, y in zip(a, b)]

    def _make(self, samples):
        buf = array("h")
        for v in samples:
            s = int(max(-1.0, min(1.0, v)) * 32767)
            buf.extend([s] * self.channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.muted or name not in self.sounds:
            return
        if name == "shot":
            self.shot_channel.play(self.sounds[name])
        else:
            self.sounds[name].play()


# ---------------------------------------------------------------- 지형
def make_tiles():
    def tile(color):
        s = pygame.Surface((TILE, TILE))
        s.fill(color)
        return s

    rng = random.Random(1)
    tiles = {}

    g = tile(GRASS)
    for _ in range(7):
        pygame.draw.circle(g, GRASS2, (rng.randrange(TILE), rng.randrange(TILE)), 2)
    tiles["grass"] = g

    f = tile(FOREST)
    for cx, cy in ((8, 8), (24, 10), (14, 22), (28, 27)):
        pygame.draw.circle(f, FOREST_DARK, (cx, cy), 7)
        pygame.draw.circle(f, FOREST_LIGHT, (cx - 2, cy - 2), 4)
    tiles["forest"] = f

    s = tile(SAND)
    for _ in range(6):
        pygame.draw.circle(s, (155, 135, 90), (rng.randrange(TILE), rng.randrange(TILE)), 1)
    tiles["sand"] = s

    for i in range(2):
        w = tile(WATER)
        for y in (6 + i * 8, 22 + i * 8):
            y %= TILE
            pygame.draw.line(w, WATER_LIGHT, (4, y), (12, y), 1)
            pygame.draw.line(w, WATER_LIGHT, (18, (y + 8) % TILE), (28, (y + 8) % TILE), 1)
        tiles[f"water{i}"] = w

    r = tile(ROAD)
    pygame.draw.line(r, (80, 76, 70), (0, 1), (TILE, 1), 2)
    pygame.draw.line(r, (80, 76, 70), (0, TILE - 2), (TILE, TILE - 2), 2)
    pygame.draw.line(r, (210, 200, 120), (4, TILE // 2), (20, TILE // 2), 2)
    tiles["road"] = r

    b = tile((140, 115, 80))
    for x in range(0, TILE, 6):
        pygame.draw.line(b, (110, 88, 60), (x, 0), (x, TILE), 1)
    pygame.draw.line(b, (70, 60, 50), (0, 2), (TILE, 2), 3)
    pygame.draw.line(b, (70, 60, 50), (0, TILE - 3), (TILE, TILE - 3), 3)
    tiles["bridge"] = b
    return tiles


class Terrain:
    """행 단위로 무한 생성되는 지형. 행 r은 화면 아래쪽부터 위로 쌓인다."""

    def __init__(self, seed):
        self.seed = seed
        self.rng = random.Random(seed)
        self.rows = {}
        self.next_row = 0
        self.river_x = COLS // 2 - 1
        self.river_w = 3
        self.road_cd = 12

    def _forest(self, r, c):
        return random.Random(self.seed * 7 + (r // 4) * 1009 + c // 3).random() < 0.35

    def _generate(self):
        r, rng = self.next_row, self.rng
        if rng.random() < 0.3:
            self.river_x += rng.choice((-1, 1))
        if rng.random() < 0.05:
            self.river_w = rng.randint(2, 4)
        self.river_x = max(2, min(COLS - 3 - self.river_w, self.river_x))

        self.road_cd -= 1
        road = self.road_cd <= 0 and rng.random() < 0.08
        if road:
            self.road_cd = 15

        row = []
        for c in range(COLS):
            in_river = self.river_x <= c < self.river_x + self.river_w
            if road:
                t = "bridge" if in_river else "road"
            elif in_river:
                t = "water"
            elif c in (self.river_x - 1, self.river_x + self.river_w):
                t = "sand"
            elif self._forest(r, c):
                t = "forest"
            else:
                t = "grass"
            row.append(t)
        self.rows[r] = row
        self.next_row += 1

    def get_row(self, r):
        while self.next_row <= r:
            self._generate()
        return self.rows[r]

    def tile_at(self, x, y, scroll):
        r = int((H - y + scroll) // TILE)
        c = max(0, min(COLS - 1, int(x // TILE)))
        return self.get_row(r)[c]

    def draw(self, surf, scroll, tiles, frame):
        s = int(scroll)
        r0 = s // TILE
        r1 = (s + H) // TILE + 1
        water = "water0" if (frame // 30) % 2 == 0 else "water1"
        for r in range(r0, r1 + 1):
            y = H - (r + 1) * TILE + s
            for c, t in enumerate(self.get_row(r)):
                surf.blit(tiles[water if t == "water" else t], (c * TILE, y))
        for old in [k for k in self.rows if k < r0 - 2]:
            del self.rows[old]


# ---------------------------------------------------------------- 플레이어
class Player:
    def __init__(self):
        self.x, self.y = W / 2, H - 90
        self.speed = 4.2
        self.shot_cd = 0
        self.invuln = 120
        self.respawn = 0  # >0 이면 격추되어 대기 중

    @property
    def active(self):
        return self.respawn == 0

    @property
    def sight(self):
        return self.x, max(20, self.y - SIGHT_DIST)

    def update(self, keys):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        k = 0.7071 if dx and dy else 1.0
        self.x = max(16, min(W - 16, self.x + dx * self.speed * k))
        self.y = max(60, min(H - 20, self.y + dy * self.speed * k))
        if self.shot_cd:
            self.shot_cd -= 1
        if self.invuln:
            self.invuln -= 1

    def draw(self, surf, frame):
        if not self.active or (self.invuln and (frame // 4) % 2):
            return
        x, y = int(self.x), int(self.y)
        flame = 6 + (frame % 4) * 2
        pygame.draw.polygon(surf, (255, 160, 40), [(x - 4, y + 12), (x + 4, y + 12), (x, y + 12 + flame)])
        body = [(x, y - 18), (x + 6, y - 4), (x + 17, y + 8), (x + 6, y + 7),
                (x + 4, y + 13), (x - 4, y + 13), (x - 6, y + 7), (x - 17, y + 8), (x - 6, y - 4)]
        pygame.draw.polygon(surf, (210, 215, 225), body)
        pygame.draw.polygon(surf, (120, 125, 140), body, 1)
        pygame.draw.line(surf, (200, 50, 50), (x - 15, y + 7), (x - 8, y + 5), 2)
        pygame.draw.line(surf, (200, 50, 50), (x + 15, y + 7), (x + 8, y + 5), 2)
        pygame.draw.ellipse(surf, (60, 140, 230), (x - 3, y - 9, 6, 10))


class Shot:
    def __init__(self, x, y, angle=0.0):
        self.x, self.y = x, y
        self.vx = math.sin(angle) * 11
        self.vy = -math.cos(angle) * 11
        self.dead = False

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -12 or not -12 < self.x < W + 12:
            self.dead = True

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        tail = (int(self.x - self.vx), int(self.y - self.vy))
        pygame.draw.line(surf, (255, 255, 160), (x, y), tail, 4)


class Item:
    """파워업 아이템. 천천히 내려오며 좌우로 튕긴다."""
    radius = 12

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx = random.choice((-1.0, 1.0))
        self.dead = False

    def update(self):
        self.y += 1.0
        self.x += self.vx
        if not 14 < self.x < W - 14:
            self.vx = -self.vx
        if self.y > H + 20:
            self.dead = True

    def draw(self, surf, frame, font):
        x, y = int(self.x), int(self.y)
        ring = (80, 170, 255) if (frame // 8) % 2 else WHITE
        pygame.draw.circle(surf, ring, (x, y), 12)
        pygame.draw.circle(surf, (20, 40, 130), (x, y), 9)
        img = font.render("P", True, (255, 230, 90))
        surf.blit(img, img.get_rect(center=(x, y + 1)))


class Bomb:
    DURATION = 30

    def __init__(self, x, y, tx, ty):
        self.sx, self.sy = x, y
        self.tx, self.ty = tx, ty
        self.t = 0
        self.dead = False

    def update(self):
        """착탄하면 True."""
        self.ty += SCROLL_SPEED
        self.t += 1
        if self.t >= self.DURATION:
            self.dead = True
            return True
        return False

    def draw(self, surf):
        k = self.t / self.DURATION
        x = self.sx + (self.tx - self.sx) * k
        y = self.sy + (self.ty - self.sy) * k
        r = max(2, int(6 - 4 * k))
        pygame.draw.circle(surf, (40, 40, 40), (int(x), int(y)), r)
        pygame.draw.circle(surf, (230, 230, 120), (int(x), int(y)), max(1, r - 2))


class EBullet:
    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dead = False

    @classmethod
    def aimed(cls, x, y, tx, ty, speed, offset=0.0):
        a = math.atan2(ty - y, tx - x) + offset
        return cls(x, y, math.cos(a) * speed, math.sin(a) * speed)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-10 < self.x < W + 10 and -10 < self.y < H + 10):
            self.dead = True

    def draw(self, surf, frame):
        c = (255, 90, 60) if (frame // 3) % 2 else (255, 200, 80)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), 4)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), 2)


# ---------------------------------------------------------------- 적
class Enemy:
    ground = False
    radius = 12
    score = 100
    fx_size = 1.0

    def __init__(self, x, y, hp=1):
        self.x, self.y = x, y
        self.hp = hp
        self.t = 0
        self.flash = 0
        self.dead = False

    def fire(self, g, offset=0.0):
        p = g.player
        g.ebullets.append(EBullet.aimed(self.x, self.y, p.x, p.y, g.bullet_speed, offset))

    def update(self, g):
        self.t += 1
        if self.flash:
            self.flash -= 1
        if self.ground:
            self.y += SCROLL_SPEED
        if not (-220 < self.y < H + 60 and -220 < self.x < W + 220):
            self.dead = True

    def aim_angle(self, g):
        return math.atan2(g.player.y - self.y, g.player.x - self.x)


class Dart(Enemy):
    """위에서 지그재그로 내려오는 소형기."""
    score = 100

    def __init__(self, x, y):
        super().__init__(x, y)
        self.x0 = x
        self.phase = random.random() * math.tau

    def update(self, g):
        super().update(g)
        self.y += 3
        self.x = self.x0 + math.sin(self.t * 0.05 + self.phase) * 30
        if 0 < self.y < H * 0.5 and random.random() < 0.004 * g.level:
            self.fire(g)

    def draw(self, surf, frame):
        x, y = int(self.x), int(self.y)
        pts = [(x, y + 12), (x + 11, y - 6), (x, y - 1), (x - 11, y - 6)]
        pygame.draw.polygon(surf, (200, 60, 60), pts)
        pygame.draw.polygon(surf, (255, 150, 150), pts, 1)
        pygame.draw.circle(surf, (255, 220, 120), (x, y + 3), 3)


class Swooper(Enemy):
    """플레이어를 향해 돌진하다가 사격 후 급선회해 이탈."""
    score = 150
    radius = 11

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx, self.vy = 0.0, 3.2
        self.turned = False
        self.dir = 1

    def update(self, g):
        super().update(g)
        p = g.player
        if not self.turned:
            self.vx = max(-2.5, min(2.5, self.vx + (p.x - self.x) * 0.003))
            if self.y > p.y - 220 or self.t > 100:
                self.turned = True
                self.dir = -1 if p.x > self.x else 1
                self.fire(g)
        else:
            self.vx += self.dir * 0.25
            self.vy = max(-5, self.vy - 0.18)
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf, frame):
        x, y = int(self.x), int(self.y)
        a = self.t * 0.25
        for i in range(3):
            ang = a + i * math.tau / 3
            ex, ey = x + math.cos(ang) * 13, y + math.sin(ang) * 13
            pygame.draw.line(surf, (200, 255, 210), (x, y), (int(ex), int(ey)), 3)
        pygame.draw.circle(surf, (60, 180, 140), (x, y), 8)
        pygame.draw.circle(surf, (230, 255, 120), (x, y), 3)


class Weaver(Enemy):
    """옆에서 물결치며 가로지르는 편대기."""
    score = 200
    radius = 12

    def __init__(self, x, y, vx):
        super().__init__(x, y)
        self.y0 = y
        self.vx = vx
        self.fire_at = random.randint(40, 110)

    def update(self, g):
        super().update(g)
        self.x += self.vx
        self.y = self.y0 + math.sin(self.t * 0.08) * 30 + self.t * 0.3
        if self.t == self.fire_at and 0 < self.x < W:
            self.fire(g)

    def draw(self, surf, frame):
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(surf, (150, 90, 30), (x - 15, y - 3, 30, 6))
        pygame.draw.ellipse(surf, (240, 150, 40), (x - 9, y - 8, 18, 16))
        pygame.draw.ellipse(surf, (255, 230, 150), (x - 4, y - 4, 8, 8))


class Turret(Enemy):
    """지상 고정 포대."""
    ground = True
    score = 300
    radius = 12

    def __init__(self, x, y):
        super().__init__(x, y)
        self.cd = random.randint(40, 120)

    def update(self, g):
        super().update(g)
        self.cd -= 1
        if self.cd <= 0:
            self.cd = max(55, 140 - g.level * 10) + random.randint(0, 40)
            if 10 < self.y < g.player.y - 60:
                self.fire(g)

    def draw_barrel(self, surf, g, length, color):
        a = self.aim_angle(g)
        x, y = int(self.x), int(self.y)
        pygame.draw.line(surf, color, (x, y), (int(x + math.cos(a) * length), int(y + math.sin(a) * length)), 4)

    def draw(self, surf, frame, g):
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(surf, (120, 120, 115), (x - 12, y - 12, 24, 24))
        pygame.draw.rect(surf, (80, 80, 78), (x - 12, y - 12, 24, 24), 2)
        pygame.draw.circle(surf, (60, 62, 66), (x, y), 8)
        self.draw_barrel(surf, g, 15, (40, 40, 44))


class Tank(Turret):
    """도로·평지를 좌우로 오가는 전차."""
    score = 250

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx = random.choice((-0.7, 0.7))

    def update(self, g):
        super().update(g)
        ahead = self.x + self.vx * 20
        if not (16 < ahead < W - 16) or g.terrain.tile_at(ahead, self.y, g.scroll) == "water":
            self.vx = -self.vx
        else:
            self.x += self.vx

    def draw(self, surf, frame, g):
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(surf, (50, 50, 40), (x - 14, y - 11, 28, 5))
        pygame.draw.rect(surf, (50, 50, 40), (x - 14, y + 6, 28, 5))
        pygame.draw.rect(surf, (110, 120, 70), (x - 12, y - 8, 24, 16))
        pygame.draw.circle(surf, (85, 95, 55), (x, y), 6)
        self.draw_barrel(surf, g, 14, (40, 45, 30))


class Fortress(Enemy):
    """대형 지상 요새. 폭탄 여러 발로 파괴."""
    ground = True
    score = 2000
    radius = 34
    fx_size = 2.5

    def __init__(self, x, y):
        super().__init__(x, y, hp=6)
        self.cd = 60

    def update(self, g):
        super().update(g)
        self.cd -= 1
        if self.cd <= 0:
            self.cd = max(50, 110 - g.level * 8)
            if 20 < self.y < H * 0.6:
                for off in (-0.4, -0.2, 0, 0.2, 0.4):
                    self.fire(g, off)

    def draw(self, surf, frame, g):
        x, y = int(self.x), int(self.y)
        pts = [(x + math.cos(i * math.tau / 8 + math.pi / 8) * 38,
                y + math.sin(i * math.tau / 8 + math.pi / 8) * 38) for i in range(8)]
        pygame.draw.polygon(surf, (95, 95, 105), pts)
        pygame.draw.polygon(surf, (60, 60, 70), pts, 3)
        for dx, dy in ((-20, -20), (20, -20), (-20, 20), (20, 20)):
            pygame.draw.circle(surf, (70, 70, 80), (x + dx, y + dy), 6)
        core = WHITE if self.flash else ((230, 50, 50) if (frame // 15) % 2 else (150, 30, 30))
        pygame.draw.circle(surf, (40, 40, 48), (x, y), 14)
        pygame.draw.circle(surf, core, (x, y), 9)
        for i in range(self.hp):
            pygame.draw.rect(surf, (90, 230, 90), (x - 17 + i * 6, y + 26, 4, 4))


# ---------------------------------------------------------------- 이펙트
class Explosion:
    def __init__(self, x, y, size=1.0, ground=False):
        self.x, self.y = x, y
        self.size = size
        self.ground = ground
        self.t = 0
        self.life = int(24 + 12 * size)
        self.dead = False
        self.parts = []
        for _ in range(int(10 * size)):
            a = random.random() * math.tau
            sp = random.uniform(1, 3.5) * size ** 0.5
            self.parts.append([x, y, math.cos(a) * sp, math.sin(a) * sp])

    def update(self):
        self.t += 1
        if self.t >= self.life:
            self.dead = True
        dy = SCROLL_SPEED if self.ground else 0
        self.y += dy
        for p in self.parts:
            p[0] += p[2]
            p[1] += p[3] + dy
            p[2] *= 0.94
            p[3] *= 0.94

    def draw(self, surf):
        k = self.t / self.life
        r = int((6 + 22 * self.size) * min(1.0, k * 2.5))
        col = (255, int(240 - 180 * k), int(150 - 130 * k))
        if k < 0.55:
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)
            pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), max(1, r // 2))
        else:
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r, 2)
        for px, py, _, _ in self.parts:
            pygame.draw.circle(surf, (255, 200, 80), (int(px), int(py)), max(1, int(3 * (1 - k))))


class Crater:
    def __init__(self, x, y, r):
        self.x, self.y, self.r = x, y, r
        self.dead = False

    def update(self):
        self.y += SCROLL_SPEED
        if self.y > H + 50:
            self.dead = True

    def draw(self, surf):
        pygame.draw.circle(surf, (45, 45, 35), (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (28, 28, 22), (int(self.x), int(self.y)), max(2, self.r - 5))


# ---------------------------------------------------------------- 게임
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.sfx = Sfx()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("SKY STRIKE")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.big = pygame.font.Font(None, 72)
        self.tiles = make_tiles()
        self.hiscore = 0
        self.reset()
        self.state = "title"

    def reset(self):
        self.terrain = Terrain(random.randrange(1 << 30))
        self.scroll = 0.0
        self.frame = 0
        self.player = Player()
        self.shots, self.bombs, self.enemies = [], [], []
        self.ebullets, self.effects, self.craters = [], [], []
        self.items = []
        self.power = 0  # POWER_SHOTS 인덱스
        self.score = 0
        self.lives = 3
        self.air_timer = 90
        self.ground_timer = 150
        self.fortress_timer = 60 * 35
        self.state = "play"

    @property
    def level(self):
        return 1 + self.frame // (60 * 30)

    @property
    def bullet_speed(self):
        return min(6.0, 3.0 + 0.35 * self.level)

    # ---------- 생성
    def land_x(self, y, margin=20):
        for _ in range(12):
            x = random.uniform(margin, W - margin)
            if self.terrain.tile_at(x, y, self.scroll) not in ("water", "bridge"):
                return x
        return None

    def spawn(self):
        self.air_timer -= 1
        if self.air_timer <= 0:
            self.air_timer = max(30, 100 - self.level * 8) + random.randint(0, 40)
            kind = random.random()
            if kind < 0.45:
                x = random.uniform(50, W - 50)
                for i in range(random.randint(3, 5)):
                    self.enemies.append(Dart(x, -20 - i * 32))
            elif kind < 0.75:
                for _ in range(random.randint(1, 2)):
                    self.enemies.append(Swooper(random.uniform(40, W - 40), -20))
            else:
                left = random.random() < 0.5
                y = random.uniform(60, 220)
                for i in range(4):
                    x = -30 - i * 40 if left else W + 30 + i * 40
                    self.enemies.append(Weaver(x, y, 2.6 if left else -2.6))

        self.ground_timer -= 1
        if self.ground_timer <= 0:
            self.ground_timer = max(45, 130 - self.level * 10) + random.randint(0, 50)
            y = -30
            x = self.land_x(y)
            if x is not None:
                cls = Tank if random.random() < 0.4 else Turret
                self.enemies.append(cls(x, y))

        self.fortress_timer -= 1
        if self.fortress_timer <= 0:
            self.fortress_timer = 60 * 40
            self.enemies.append(Fortress(random.uniform(90, W - 90), -60))

    # ---------- 처리
    def kill(self, e):
        e.dead = True
        self.score += e.score
        self.effects.append(Explosion(e.x, e.y, e.fx_size, e.ground))
        self.sfx.play("boom_big" if isinstance(e, Fortress) else "boom")
        if e.ground:
            self.craters.append(Crater(e.x, e.y, int(e.radius * 0.9)))
        if isinstance(e, Fortress) or random.random() < (0.15 if e.ground else 0.08):
            self.items.append(Item(e.x, e.y))

    def damage(self, e):
        e.hp -= 1
        e.flash = 6
        if e.hp <= 0:
            self.kill(e)
        else:
            self.sfx.play("clang")

    def player_hit(self):
        p = self.player
        self.effects.append(Explosion(p.x, p.y, 2.0))
        self.sfx.play("die")
        self.lives -= 1
        self.power = max(0, self.power - 1)
        self.ebullets.clear()
        p.respawn = 100

    def fire_shots(self):
        p = self.player
        n, spread = POWER_SHOTS[self.power], POWER_SPREAD[self.power]
        for i in range(n):
            k = i / (n - 1) * 2 - 1  # -1 ~ 1
            self.shots.append(Shot(p.x + k * 7, p.y - 12, k * spread))
        p.shot_cd = 7
        self.sfx.play("shot")

    def pick_item(self, it):
        it.dead = True
        if self.power < len(POWER_SHOTS) - 1:
            self.power += 1
            self.sfx.play("powerup")
        else:
            self.score += 1000
            self.sfx.play("bonus")

    def drop_bomb(self):
        p = self.player
        if p.active and not self.bombs:
            sx, sy = p.sight
            self.bombs.append(Bomb(p.x, p.y - 10, sx, sy))
            self.sfx.play("bomb")

    def update(self, keys):
        self.frame += 1
        self.scroll += SCROLL_SPEED
        p = self.player

        if p.respawn:
            p.respawn -= 1
            if p.respawn == 0:
                if self.lives <= 0:
                    self.state = "over"
                    self.hiscore = max(self.hiscore, self.score)
                    self.sfx.play("gameover")
                    return
                p.x, p.y, p.invuln = W / 2, H - 90, 150
        else:
            p.update(keys)
            if (keys[pygame.K_z] or keys[pygame.K_SPACE]) and p.shot_cd == 0:
                self.fire_shots()

        self.spawn()

        for s in self.shots:
            s.update()
        for e in self.enemies:
            e.update(self)
        for b in self.ebullets:
            b.update()
        for fx in self.effects:
            fx.update()
        for c in self.craters:
            c.update()
        for it in self.items:
            it.update()
            if p.active and dist(it.x, it.y, p.x, p.y) < it.radius + 12:
                self.pick_item(it)

        # 폭탄 착탄
        for b in self.bombs:
            if b.update():
                self.effects.append(Explosion(b.tx, b.ty, 0.6, ground=True))
                self.sfx.play("impact")
                for e in self.enemies:
                    if e.ground and not e.dead and dist(e.x, e.y, b.tx, b.ty) < e.radius + 16:
                        self.damage(e)

        # 기총 vs 공중 적
        for s in self.shots:
            for e in self.enemies:
                if not e.ground and not e.dead and dist(s.x, s.y, e.x, e.y) < e.radius + 4:
                    s.dead = True
                    self.damage(e)
                    break

        # 플레이어 피격
        if p.active and not p.invuln:
            hit = any(dist(b.x, b.y, p.x, p.y) < 8 for b in self.ebullets)
            for e in self.enemies:
                if not e.ground and not e.dead and dist(e.x, e.y, p.x, p.y) < e.radius + 8:
                    self.kill(e)
                    hit = True
            if hit:
                self.player_hit()

        for name in ("shots", "bombs", "enemies", "ebullets", "effects", "craters", "items"):
            setattr(self, name, [o for o in getattr(self, name) if not o.dead])

    # ---------- 그리기
    def text(self, msg, font, color, center):
        img = font.render(msg, True, color)
        self.screen.blit(img, img.get_rect(center=center))

    def draw_sight(self):
        p = self.player
        if not p.active:
            return
        sx, sy = p.sight
        locked = any(e.ground and dist(e.x, e.y, sx, sy) < e.radius + 16 for e in self.enemies)
        c = (255, 60, 60) if locked else (255, 255, 255)
        x, y = int(sx), int(sy)
        pygame.draw.circle(self.screen, c, (x, y), 11, 2)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(self.screen, c, (x + dx * 6, y + dy * 6), (x + dx * 15, y + dy * 15), 2)

    def draw_hud(self):
        bar = pygame.Surface((W, 30), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 140))
        self.screen.blit(bar, (0, 0))
        self.screen.blit(self.font.render(f"SCORE {self.score:07d}", True, WHITE), (8, 6))
        self.text(f"HI {max(self.hiscore, self.score):07d}", self.font, (255, 220, 120), (W // 2 + 40, 16))
        for i in range(max(0, self.lives)):
            x = W - 16 - i * 18
            pygame.draw.polygon(self.screen, (210, 215, 225), [(x, 7), (x + 7, 23), (x - 7, 23)])
        self.screen.blit(self.font.render(f"LV {self.level}", True, (180, 220, 255)), (8, H - 26))
        shot = self.font.render(f"SHOT x{POWER_SHOTS[self.power]}", True, (255, 230, 90))
        self.screen.blit(shot, shot.get_rect(bottomright=(W - 8, H - 6)))
        if self.sfx.muted:
            self.text("MUTE", self.font, (200, 200, 200), (W // 2, H - 16))

    def draw(self):
        sc = self.screen
        self.terrain.draw(sc, self.scroll, self.tiles, self.frame)
        for c in self.craters:
            c.draw(sc)
        for e in self.enemies:
            if e.ground:
                e.draw(sc, self.frame, self)
        for b in self.bombs:
            b.draw(sc)
        if self.state == "play":
            self.draw_sight()
        for it in self.items:
            it.draw(sc, self.frame, self.font)
        for e in self.enemies:
            if not e.ground:
                e.draw(sc, self.frame)
        for s in self.shots:
            s.draw(sc)
        self.player.draw(sc, self.frame)
        for b in self.ebullets:
            b.draw(sc, self.frame)
        for fx in self.effects:
            fx.draw(sc)
        self.draw_hud()

        if self.state in ("title", "over", "pause"):
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            sc.blit(shade, (0, 0))
        if self.state == "title":
            self.text("SKY STRIKE", self.big, (255, 220, 120), (W // 2, H // 2 - 90))
            lines = ["Arrows / WASD : Move", "Z / Space : Shoot (air)", "X : Bomb (ground)",
                     "Get [P] items : 2 > 4 > 8 > 16 shots",
                     "P : Pause   M : Sound   ESC : Quit", "", "Press ENTER to start"]
            for i, line in enumerate(lines):
                self.text(line, self.font, WHITE, (W // 2, H // 2 - 10 + i * 30))
        elif self.state == "over":
            self.text("GAME OVER", self.big, (255, 90, 90), (W // 2, H // 2 - 40))
            self.text(f"SCORE {self.score}", self.font, WHITE, (W // 2, H // 2 + 20))
            self.text("Press ENTER or R to restart", self.font, WHITE, (W // 2, H // 2 + 60))
        elif self.state == "pause":
            self.text("PAUSED", self.big, WHITE, (W // 2, H // 2))

        pygame.display.flip()

    # ---------- 루프
    def handle_key(self, key):
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        if key == pygame.K_m:
            self.sfx.muted = not self.sfx.muted
        elif self.state == "title" and key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            self.reset()
            self.sfx.play("start")
        elif self.state == "over" and key in (pygame.K_RETURN, pygame.K_r):
            self.reset()
            self.sfx.play("start")
        elif self.state == "play":
            if key == pygame.K_x:
                self.drop_bomb()
            elif key == pygame.K_p:
                self.state = "pause"
        elif self.state == "pause" and key == pygame.K_p:
            self.state = "play"

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
            if self.state == "play":
                self.update(pygame.key.get_pressed())
            elif self.state == "title":
                self.scroll += SCROLL_SPEED  # 타이틀 화면에서도 배경 스크롤
                self.frame += 1
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
