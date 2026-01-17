import pygame
import random
import math
from pygame.locals import *

# --- Configuration Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 864, 936
FPS = 60
GROUND_LEVEL = 768
PIPE_GAP, PIPE_FREQ = 150, 1.5
SCROLL_SPEED, BG_SCROLL_SPEED = 240, 60
GRAVITY, JUMP_STRENGTH = 30, -8
SHAKE_INTENSITY, SHAKE_DURATION = 15, 0.4
FLASH_DURATION, FLAP_SPEED = 0.1, 0.1

WHITE, BLACK, RED, BLUE, GREEN, ORANGE = (255,)*3, (0,)*3, (255, 0, 0), (30, 80, 250), (0, 150, 0), (255, 140, 0)

# --- Initialization ---
pygame.mixer.pre_init(48000, -16, 2, 4096) 
pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
render_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird")
font = pygame.font.Font('04B_19.ttf', 60)

# Game States
STATE_MENU, STATE_PLAYING, STATE_GAMEOVER = 0, 1, 2
game_state = STATE_MENU

# --- Utility Functions ---
def render_score(score_val, color=WHITE):
    """Renders text with a simple drop shadow."""
    text = str(score_val)
    main_surf = font.render(text, True, color)
    shadow_surf = font.render(text, True, BLACK)
    w, h = main_surf.get_size()
    surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    surf.blit(shadow_surf, (2, 2))
    surf.blit(main_surf, (0, 0))
    return surf.convert_alpha()

def get_shrunk_mask(image, factor=0.92):
    """Creates a slightly smaller collision mask for more 'fair' gameplay."""
    mask = pygame.mask.from_surface(image)
    if factor >= 1.0: return mask
    size = mask.get_size()
    shrunk_size = (max(1, int(size[0] * factor)), max(1, int(size[1] * factor)))
    shrunk_mask = mask.scale(shrunk_size)
    full_mask = pygame.mask.Mask(size)
    full_mask.draw(shrunk_mask, ((size[0] - shrunk_size[0]) // 2, (size[1] - shrunk_size[1]) // 2))
    return full_mask

# --- Asset Loading ---
bg = pygame.image.load('img/bg.png').convert()
bg_long = pygame.image.load('img/bglong.png').convert()
ground = pygame.image.load('img/ground.png').convert()
button_img = pygame.image.load('img/restart.png').convert()
pipe_img = pygame.image.load('img/pipe.png').convert_alpha()
pipe_img_flipped = pygame.transform.flip(pipe_img, False, True)
BIRD_IMAGES = [pygame.image.load(f'img/bird{i}.png').convert_alpha() for i in range(1, 4)]
BIRD_MASKS = [get_shrunk_mask(img, 0.98) for img in BIRD_IMAGES]
pipe_mask = get_shrunk_mask(pipe_img, 0.98)
pipe_mask_flipped = get_shrunk_mask(pipe_img_flipped, 0.98)

# Audio
flap_fx = pygame.mixer.Sound('audio/sfx_wing.wav')
hit_fx = pygame.mixer.Sound('audio/sfx_hit.wav')
point_fx = pygame.mixer.Sound('audio/sfx_point.wav')
die_fx = pygame.mixer.Sound('audio/sfx_die.wav')
swoosh_fx = pygame.mixer.Sound('audio/sfx_swooshing.wav')
pygame.mixer.music.load('audio/bg_music.mp3')
pygame.mixer.music.set_volume(0.5)

# High Score persistence
try:
    with open('highscore.txt', 'r') as f: high_score = int(f.read())
except: high_score = 0

def reset_game():
    """Resets all game variables for a new round."""
    global score, score_surface, score_rect, game_state, hit_played, die_played, pipe_timer, new_record_set
    global shake_duration, flash_alpha, run_timer, current_scroll_speed, current_pipe_gap, current_pipe_freq
    global bg_long_scroll, game_over_surf, pipe_move_speed
    pipe_group.empty()
    particle_group.empty()
    flappy.rect.center = [100, SCREEN_HEIGHT // 2]
    flappy.vel = flappy.angle = score = pipe_timer = run_timer = bg_long_scroll = pipe_move_speed = shake_duration = flash_alpha = 0
    score_surface = render_score(score, WHITE)
    score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
    current_scroll_speed, current_pipe_gap, current_pipe_freq = SCROLL_SPEED, PIPE_GAP, PIPE_FREQ
    game_state, hit_played, die_played, new_record_set, game_over_surf = STATE_MENU, False, False, False, None

# --- Game Classes ---
class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.images, self.masks = BIRD_IMAGES, BIRD_MASKS
        self.index = self.animation_timer = self.hover_timer = self.vel = self.angle = 0
        self.image, self.mask = self.images[0], self.masks[0]
        self.rect = self.image.get_rect(center=(x, y))
        # Caching rotations to avoid expensive runtime calculations
        self.rotation_cache, self.mask_cache = {}, {}
        for idx in range(len(self.images)):
            for ang in range(-85, 25):
                img = pygame.transform.rotate(self.images[idx], ang)
                self.rotation_cache[(idx, ang)], self.mask_cache[(idx, ang)] = img, get_shrunk_mask(img)

    def update(self, dt):
        if game_state == STATE_MENU:
            # Gentle hover effect on menu
            self.hover_timer += dt
            self.rect.centery = (SCREEN_HEIGHT / 2) + math.sin(self.hover_timer * 8) * 15
            self.angle = 0
        else:
            # Apply gravity
            self.vel = min(self.vel + GRAVITY * dt, 15)
            if self.rect.bottom < GROUND_LEVEL: self.rect.y += self.vel
            else: self.rect.bottom, self.vel = GROUND_LEVEL, 0

        if game_state != STATE_GAMEOVER:
            # Flap animation
            self.animation_timer += dt
            if self.animation_timer > FLAP_SPEED:
                self.animation_timer, self.index = 0, (self.index + 1) % len(self.images)
            # Stop flapping if falling fast
            if self.vel > 7: self.index, self.animation_timer = 1, 0
            
            # Smooth Rotation Logic: Interpolate towards target angle based on velocity
            target_angle = 20 if self.vel < 0 else 20 - (self.vel / 15) * 100
            lerp_speed = 5.0 if target_angle > self.angle else 3.0
            self.angle += (target_angle - self.angle) * lerp_speed * dt
        else:
            # Rapid nose-dive on death
            self.angle += (-80 - self.angle) * 8.0 * dt

        # Update image and mask from cache based on current state
        snapped_angle = max(-80, min(20, int(self.angle)))
        cache_key = (self.index, snapped_angle)
        if cache_key not in self.rotation_cache:
            img = pygame.transform.rotate(self.images[self.index], snapped_angle)
            self.rotation_cache[cache_key], self.mask_cache[cache_key] = img, get_shrunk_mask(img)
        self.image, self.mask = self.rotation_cache[cache_key], self.mask_cache[cache_key]

class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position, image, mask, gap, move_speed=0, r_offset=0, r_freq=1.0):
        super().__init__()
        self.image, self.mask, self.position, self.gap, self.move_speed, self.r_offset, self.r_freq = image, mask, position, gap, move_speed, r_offset, r_freq
        self.rect = self.image.get_rect(bottomleft=(x, y - gap/2) if position == 1 else (0, 0))
        if position == -1: self.rect.topleft = (x, y + gap/2)
        self.initial_rect_y, self.scored = self.rect.y, False

    def update(self, dt, speed):
        self.rect.x -= speed * dt
        # Oscillating vertical movement for increased difficulty
        if self.move_speed > 0:
            new_y = self.initial_rect_y + math.sin(pygame.time.get_ticks()/1000.0 * self.r_freq + self.r_offset) * (30 * self.move_speed)
            # Boundary checks to keep pipes from completely leaving the playable area
            if self.position == 1: new_y = min(new_y, 0)
            else: new_y = max(new_y, GROUND_LEVEL - 560)
            self.rect.y = new_y
        if self.rect.right < 0: self.kill()

class Button:
    def __init__(self, x, y, image):
        self.img = image
        self.hover_img = pygame.transform.scale(image, (int(image.get_width()*1.1), int(image.get_height()*1.1)))
        self.rect = self.img.get_rect(topleft=(x, y))
        self.hover_rect = self.hover_img.get_rect(center=self.rect.center)

    def draw(self, surface, forced=False):
        res = False
        if self.rect.collidepoint(pygame.mouse.get_pos()) or forced:
            surface.blit(self.hover_img, self.hover_rect)
            if pygame.mouse.get_pressed()[0]: res = True
        else: surface.blit(self.img, self.rect)
        return res

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color):
        super().__init__()
        size = random.randint(4, 8)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size//2, size//2), size//2)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx, self.vy, self.life = random.uniform(-2, 2), random.uniform(-2, 2), 1.0

    def update(self, dt):
        self.life -= dt
        self.rect.x, self.rect.y = self.rect.x + self.vx, self.rect.y + self.vy
        if self.life <= 0: self.kill()
        else: self.image.set_alpha(int(255 * self.life))

# --- Object Instantiation ---
bird_group, pipe_group, particle_group = pygame.sprite.GroupSingle(Bird(100, SCREEN_HEIGHT//2)), pygame.sprite.Group(), pygame.sprite.Group()
flappy = bird_group.sprite
button = Button(SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT//2 - 100, button_img)

# Initial State Variables
ground_scroll = bg_scroll = bg_long_scroll = pipe_timer = run_timer = score = shake_duration = flash_alpha = restart_delay = 0
current_scroll_speed, current_bg_speed, current_pipe_gap, current_pipe_freq, pipe_move_speed, score_scale = SCROLL_SPEED, BG_SCROLL_SPEED, PIPE_GAP, PIPE_FREQ, 0, 1.0
score_surface = render_score(score)
score_rect = score_surface.get_rect(center=(SCREEN_WIDTH//2, 50))
menu_text_surf = render_score("PRESS SPACE TO FLAP", ORANGE)
hit_played = die_played = new_record_set = False
game_over_surf = None

# --- Main Game Loop ---
run = True
while run:
    dt = clock.tick(FPS) / 1000.0
    evs = pygame.event.get()
    
    # Screen Shake effect logic
    ox = oy = 0
    if shake_duration > 0:
        intense = int(SHAKE_INTENSITY * (shake_duration / SHAKE_DURATION))
        shake_duration -= dt
        if intense > 0: ox, oy = random.randint(-intense, intense), random.randint(-intense, intense)

    # Parallax Scrolling Background
    render_surface.blit(bg_long, (bg_long_scroll, 0)); render_surface.blit(bg_long, (bg_long_scroll + 1280, 0))
    render_surface.blit(bg, (bg_scroll, 0)); render_surface.blit(bg, (bg_scroll + SCREEN_WIDTH, 0))
    
    # Update and Draw Entities
    pipe_group.draw(render_surface); particle_group.draw(render_surface); bird_group.draw(render_surface)
    bird_group.update(dt); particle_group.update(dt)
    render_surface.blit(ground, (ground_scroll, GROUND_LEVEL))

    if game_state == STATE_PLAYING:
        run_timer += dt
        
        # Difficulty Scaling: Speed up and tighten gaps over time
        scale = min((run_timer / 300.0)**0.5, 1.0)
        current_scroll_speed, current_pipe_gap, current_pipe_freq = SCROLL_SPEED + scale*160, PIPE_GAP - scale*50, PIPE_FREQ - scale*0.7
        current_bg_speed, pipe_move_speed = current_scroll_speed/4, min(0.4 + ((score-5)**0.5)*0.3, 4.0) if score >= 5 else 0

        # Score Tracking
        for p in pipe_group:
            if not p.scored and flappy.rect.left > p.rect.right and p.position == -1:
                score += 1
                if score > high_score: new_record_set = True
                score_surface = render_score(score, RED if new_record_set else WHITE)
                score_rect, score_scale = score_surface.get_rect(center=(SCREEN_WIDTH//2, 50)), 1.4
                point_fx.play(); p.scored = True

        # Collision Handling
        if flappy.rect.bottom >= GROUND_LEVEL or flappy.rect.top < 0 or pygame.sprite.spritecollide(flappy, pipe_group, False, pygame.sprite.collide_mask):
            game_state = STATE_GAMEOVER
            if not hit_played:
                for _ in range(15): particle_group.add(Particle(flappy.rect.centerx, flappy.rect.centery, WHITE))
                shake_duration, flash_alpha, hit_played = SHAKE_DURATION, 255, True
                if flappy.rect.bottom < GROUND_LEVEL: hit_fx.play(); swoosh_fx.play()
                die_fx.play(); pygame.mixer.music.stop()
                game_over_surf = render_score(f'NEW RECORD: {score}!' if new_record_set else f'HIGH SCORE: {high_score}', GREEN if new_record_set else BLUE)
                if score > high_score:
                    high_score = score
                    with open('highscore.txt', 'w') as f: f.write(str(high_score))
        
        # Pipe management
        pipe_group.update(dt, current_scroll_speed)
        pipe_timer += dt
        if pipe_timer > current_pipe_freq:
            h, off, f = random.randint(-100, 100), random.uniform(0, math.pi*2), random.uniform(0.8, 1.2)
            pipe_group.add(Pipe(SCREEN_WIDTH, SCREEN_HEIGHT//2+h, -1, pipe_img, pipe_mask, current_pipe_gap, pipe_move_speed, off, f))
            pipe_group.add(Pipe(SCREEN_WIDTH, SCREEN_HEIGHT//2+h, 1, pipe_img_flipped, pipe_mask_flipped, current_pipe_gap, pipe_move_speed, off, f))
            pipe_timer = 0

    # Scrolling backgrounds when not in game-over
    if game_state != STATE_GAMEOVER:
        ground_scroll = (ground_scroll - current_scroll_speed*dt) % -35
        bg_scroll = (bg_scroll - current_bg_speed*dt) % -SCREEN_WIDTH
        bg_long_scroll = (bg_long_scroll - (current_bg_speed/2)*dt) % -1280

    # UI Rendering
    if game_state != STATE_MENU:
        if score_scale > 1.0:
            score_scale = max(1.0, score_scale - 2.0*dt)
            s = pygame.transform.scale(score_surface, (int(score_surface.get_width()*score_scale), int(score_surface.get_height()*score_scale)))
            render_surface.blit(s, s.get_rect(center=(SCREEN_WIDTH//2, 50)))
        else: render_surface.blit(score_surface, score_rect)

    if game_state == STATE_MENU:
        ps = 1.0 + 0.05 * math.sin(pygame.time.get_ticks() * 0.005)
        sm = pygame.transform.scale(menu_text_surf, (int(menu_text_surf.get_width()*ps), int(menu_text_surf.get_height()*ps)))
        render_surface.blit(sm, sm.get_rect(center=(SCREEN_WIDTH//2, 150)))
    elif game_state == STATE_GAMEOVER:
        if game_over_surf: render_surface.blit(game_over_surf, game_over_surf.get_rect(center=(SCREEN_WIDTH//2, 120)))
        if restart_delay > 0:
            button.draw(render_surface, True); restart_delay -= 1
            if restart_delay == 0: reset_game(); swoosh_fx.play()
        elif button.draw(render_surface): reset_game(); swoosh_fx.play()

    # Flash effect on hit
    if flash_alpha > 0:
        fs = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); fs.fill(WHITE); fs.set_alpha(flash_alpha)
        render_surface.blit(fs, (0, 0)); flash_alpha = max(0, flash_alpha - 1500*dt)

    # Final display blit with screen shake offsets
    screen.fill(BLACK); screen.blit(render_surface, (ox, oy))
    
    # Event Handling
    for e in evs:
        if e.type == QUIT: run = False
        if e.type == KEYDOWN and e.key == K_SPACE:
            if game_state == STATE_MENU: game_state = STATE_PLAYING; swoosh_fx.play(); pygame.mixer.music.play(-1)
            if game_state == STATE_PLAYING: flappy.vel = JUMP_STRENGTH; flap_fx.play()
            elif game_state == STATE_GAMEOVER and restart_delay == 0: restart_delay = 10
    pygame.display.flip()
pygame.quit()