import pygame
import random
import math
from pygame.locals import *

# --- Configuration Constants ---
SCREEN_WIDTH = 864
SCREEN_HEIGHT = 936
FPS = 60
GROUND_LEVEL = 768
PIPE_GAP = 150
PIPE_FREQ = 1.5  # Seconds
SCROLL_SPEED = 240
BG_SCROLL_SPEED = 60
GRAVITY = 30
JUMP_STRENGTH = -8
SHAKE_INTENSITY = 15
SHAKE_DURATION = 0.4
FLASH_DURATION = 0.1
FLAP_SPEED = 0.1

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (30, 80, 250)
GREEN = (0, 150, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 140, 0)

# --- Initialization ---
pygame.mixer.pre_init(48000, -16, 2, 4096) 
pygame.init()

clock = pygame.time.Clock()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
render_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird")

# Define font
font = pygame.font.Font('04B_19.ttf', 60)

# Game States
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2
game_state = STATE_MENU

# --- Game Variables ---
ground_scroll = 0
bg_scroll = 0
bg_long_scroll = 0
pipe_timer = 0
run_timer = 0
current_scroll_speed = SCROLL_SPEED
current_bg_speed = BG_SCROLL_SPEED
current_pipe_gap = PIPE_GAP
current_pipe_freq = PIPE_FREQ
pipe_move_speed = 0
score = 0
pass_pipe = False
hit_played = False
die_played = False
shake_duration = 0
flash_alpha = 0
new_record_set = False
score_scale = 1.0

# --- Assets ---
def render_score(score_val, color=WHITE):
    text = str(score_val)
    main_surf = font.render(text, True, color)
    shadow_surf = font.render(text, True, BLACK)
    w, h = main_surf.get_size()
    surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    surf.blit(shadow_surf, (2, 2))
    surf.blit(main_surf, (0, 0))
    return surf.convert_alpha()

# Initialize Score Surface
score_surface = render_score(score, WHITE)
score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))

# Pre-render Menu Text
menu_text_surf = render_score("PRESS SPACE TO FLAP", ORANGE)
menu_text_rect = menu_text_surf.get_rect(center=(SCREEN_WIDTH // 2, 150))
game_over_surf = None

# Load high score
try:
    with open('highscore.txt', 'r') as f:
        high_score = int(f.read())
except:
    high_score = 0

# Load Images
bg = pygame.image.load('img/bg.png').convert()
bg_long = pygame.image.load('img/bglong.png').convert()
ground = pygame.image.load('img/ground.png').convert()
button_img = pygame.image.load('img/restart.png').convert()
pipe_img = pygame.image.load('img/pipe.png').convert_alpha()
pipe_img_flipped = pygame.transform.flip(pipe_img, False, True)

# Bird Images (Pre-loaded)
BIRD_IMAGES = [pygame.image.load(f'img/bird{i}.png').convert_alpha() for i in range(1, 4)]

def get_shrunk_mask(image, factor=0.92):
    mask = pygame.mask.from_surface(image)
    if factor >= 1.0:
        return mask
    size = mask.get_size()
    shrunk_size = (max(1, int(size[0] * factor)), max(1, int(size[1] * factor)))
    shrunk_mask = mask.scale(shrunk_size)
    full_mask = pygame.mask.Mask(size)
    full_mask.draw(shrunk_mask, ((size[0] - shrunk_size[0]) // 2, (size[1] - shrunk_size[1]) // 2))
    return full_mask

BIRD_MASKS = [get_shrunk_mask(img) for img in BIRD_IMAGES]

# Pre-calculate masks
pipe_mask = get_shrunk_mask(pipe_img, 0.98)
pipe_mask_flipped = get_shrunk_mask(pipe_img_flipped, 0.98)

# Load Sounds
flap_fx = pygame.mixer.Sound('audio/sfx_wing.wav')
hit_fx = pygame.mixer.Sound('audio/sfx_hit.wav')
point_fx = pygame.mixer.Sound('audio/sfx_point.wav')
die_fx = pygame.mixer.Sound('audio/sfx_die.wav')
swoosh_fx = pygame.mixer.Sound('audio/sfx_swooshing.wav')

# Background Music
pygame.mixer.music.load('audio/bg_music.mp3')
pygame.mixer.music.set_volume(0.5)

def reset_game():
    global score, score_surface, score_rect, game_state, hit_played, die_played, pass_pipe, pipe_timer, new_record_set
    global shake_duration, flash_alpha, run_timer, current_scroll_speed, current_pipe_gap, current_pipe_freq, bg_long_scroll
    global game_over_surf, pipe_move_speed
    pipe_group.empty()
    particle_group.empty()
    flappy.rect.x = 100
    flappy.rect.y = SCREEN_HEIGHT / 2
    flappy.vel = 0
    score = 0
    score_surface = render_score(score, WHITE)
    score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
    pass_pipe = False
    pipe_timer = 0
    run_timer = 0
    bg_long_scroll = 0
    current_scroll_speed = SCROLL_SPEED
    current_pipe_gap = PIPE_GAP
    current_pipe_freq = PIPE_FREQ
    pipe_move_speed = 0
    game_state = STATE_MENU
    hit_played = False
    die_played = False
    new_record_set = False
    shake_duration = 0
    flash_alpha = 0
    game_over_surf = None
    return score

class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.images = BIRD_IMAGES
        self.masks = BIRD_MASKS
        self.index = 0
        self.animation_timer = 0
        self.hover_timer = 0
        
        self.image = self.images[self.index]
        self.mask = self.masks[self.index]
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        self.vel = 0
        self.rotation_cache = {}
        self.mask_cache = {}

    def update(self, dt):
        if game_state == STATE_MENU:
            self.hover_timer += dt
            self.rect.centery = (SCREEN_HEIGHT / 2) + math.sin(self.hover_timer * 8) * 15
        else:
            self.vel += GRAVITY * dt
            if self.vel > 15:
                self.vel = 15
            if self.rect.bottom < GROUND_LEVEL:
                self.rect.y += self.vel
            else:
                self.rect.bottom = GROUND_LEVEL
                self.vel = 0

        if game_state != STATE_GAMEOVER:
            # Animation
            self.animation_timer += dt
            if self.animation_timer > FLAP_SPEED:
                self.animation_timer = 0
                self.index = (self.index + 1) % len(self.images)
            
            # Rotation
            angle = int(self.vel * -3)
            cache_key = (self.index, angle)
            if cache_key not in self.rotation_cache:
                rotated_img = pygame.transform.rotate(self.images[self.index], angle)
                self.rotation_cache[cache_key] = rotated_img
                self.mask_cache[cache_key] = get_shrunk_mask(rotated_img)
            
            self.image = self.rotation_cache[cache_key]
            self.mask = self.mask_cache[cache_key]
        else:
            cache_key = (self.index, -90)
            if cache_key not in self.rotation_cache:
                rotated_img = pygame.transform.rotate(self.images[self.index], -90)
                self.rotation_cache[cache_key] = rotated_img
                self.mask_cache[cache_key] = pygame.mask.from_surface(rotated_img)
            
            self.image = self.rotation_cache[cache_key]
            self.mask = self.mask_cache[cache_key]

class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position, image, mask, gap, move_speed=0, random_offset=0, random_freq=1.0):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.mask = mask
        self.rect = self.image.get_rect()
        self.move_speed = move_speed
        self.position = position
        self.gap = gap
        self.random_offset = random_offset
        self.random_freq = random_freq
        
        if position == 1:
            self.rect.bottomleft = [x, y - gap / 2]
        if position == -1:
            self.rect.topleft = [x, y + gap / 2]
        
        self.initial_rect_y = self.rect.y

    def update(self, dt, speed):
        self.rect.x -= speed * dt
        
        # Vertical movement using sine wave
        if self.move_speed > 0:
            time_sec = pygame.time.get_ticks() / 1000.0
            displacement = math.sin(time_sec * self.random_freq + self.random_offset) * (30 * self.move_speed)
            new_y = self.initial_rect_y + displacement
            
            # Boundary checks: Ensure top/bottom of pipe sprites don't enter the screen
            if self.position == 1: # Top Pipe (image is sticking out above)
                if new_y > 0: 
                    new_y = 0
            else: # Bottom Pipe (image is sticking out below ground)
                if new_y + 560 < GROUND_LEVEL:
                    new_y = GROUND_LEVEL - 560
            
            self.rect.y = new_y

        if self.rect.right < 0:
            self.kill()

class Button():
    def __init__(self, x, y, image):
        self.original_image = image
        self.hover_image = pygame.transform.scale(
            image, (int(image.get_width() * 1.1), int(image.get_height() * 1.1)))
        self.rect = self.original_image.get_rect(topleft=(x, y))
        self.hover_rect = self.hover_image.get_rect(center=self.rect.center)

    def draw(self, surface, forced_pressed=False):
        reset = False
        pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(pos) or forced_pressed:
            surface.blit(self.hover_image, self.hover_rect)
            if pygame.mouse.get_pressed()[0] == 1:
                reset = True
        else:
            surface.blit(self.original_image, self.rect)
        return reset

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color, size_range=(4, 8), vel_range=(-2, 2), lifetime=1.0):
        pygame.sprite.Sprite.__init__(self)
        self.size = random.randint(*size_range)
        if self.size < 1: self.size = 1
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (self.size // 2, self.size // 2), self.size // 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.vel_x = random.uniform(*vel_range)
        self.vel_y = random.uniform(*vel_range)
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self, dt):
        self.lifetime -= dt
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        if self.lifetime <= 0:
            self.kill()
        else:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            self.image.set_alpha(alpha)

# --- Instantiate Objects ---
bird_group = pygame.sprite.GroupSingle()
flappy = Bird(100, int(SCREEN_HEIGHT / 2))
bird_group.add(flappy)
pipe_group = pygame.sprite.Group()
particle_group = pygame.sprite.Group()
button = Button(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 - 100, button_img)

# --- Main Loop ---
run = True
restart_delay = 0

while run:
    dt = clock.tick(FPS) / 1000.0
    event_list = pygame.event.get()

    # Screen Shake
    offset_x = 0
    offset_y = 0
    if shake_duration > 0:
        # Calculate current intensity based on remaining time (linear decay)
        current_intensity = int(SHAKE_INTENSITY * (shake_duration / SHAKE_DURATION))
        shake_duration -= dt
        if current_intensity > 0:
            offset_x = random.randint(-current_intensity, current_intensity)
            offset_y = random.randint(-current_intensity, current_intensity)
        else:
            shake_duration = 0
            offset_x = 0
            offset_y = 0

    # Drawing
    # Parallax Background (Slowest - Long BG)
    render_surface.blit(bg_long, (bg_long_scroll, 0))
    render_surface.blit(bg_long, (bg_long_scroll + 1280, 0)) # bglong is 1280 wide

    # Standard Background (Medium speed)
    render_surface.blit(bg, (bg_scroll, 0))
    render_surface.blit(bg, (bg_scroll + SCREEN_WIDTH, 0))

    pipe_group.draw(render_surface)
    particle_group.draw(render_surface)
    bird_group.draw(render_surface)
    
    bird_group.update(dt)
    particle_group.update(dt)

    render_surface.blit(ground, (ground_scroll, GROUND_LEVEL))

    # Logic
    if game_state == STATE_PLAYING:
        run_timer += dt
        
        # Difficulty scaling
        scale = min((run_timer / 300.0) ** 0.5, 1.0)
        current_scroll_speed = SCROLL_SPEED + (scale * 160)
        current_pipe_gap = PIPE_GAP - (scale * 50)
        current_pipe_freq = PIPE_FREQ - (scale * 0.7)
        current_bg_speed = current_scroll_speed / 4

        # Vertical pipe movement difficulty scaling
        if score >= 5:
            # Starts very slow (0.4) and increases with a diminishing rate
            # Formula: base_speed + (sqrt(score_diff) * growth_factor)
            pipe_move_speed = min(0.4 + ((score - 5) ** 0.5) * 0.3, 4.0)
        else:
            pipe_move_speed = 0

        # Score
        if len(pipe_group) > 0:
            if flappy.rect.left > pipe_group.sprites()[0].rect.left and \
               flappy.rect.right < pipe_group.sprites()[0].rect.right and not pass_pipe:
                pass_pipe = True
            if pass_pipe:
                if flappy.rect.left > pipe_group.sprites()[0].rect.right:
                    score += 1
                    if score > high_score:
                        new_record_set = True
                    color = RED if new_record_set else WHITE
                    score_surface = render_score(score, color)
                    score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
                    pass_pipe = False
                    point_fx.play()
                    score_scale = 1.4

        # Collisions
        pipe_hit = pygame.sprite.spritecollide(flappy, pipe_group, False, pygame.sprite.collide_mask)
        if flappy.rect.bottom >= GROUND_LEVEL or flappy.rect.top < 0 or pipe_hit:
            game_state = STATE_GAMEOVER
            if not hit_played:
                for _ in range(15):
                    particle_group.add(Particle(flappy.rect.centerx, flappy.rect.centery, WHITE))
                
                shake_duration = SHAKE_DURATION
                flash_alpha = 255
                if flappy.rect.bottom < GROUND_LEVEL:
                    hit_fx.play()
                    if pipe_hit:
                        swoosh_fx.play()
                die_fx.play()
                hit_played = True
                pygame.mixer.music.stop()
                
                # Pre-render game over text
                res_color = GREEN if new_record_set else BLUE
                res_text = f'NEW RECORD: {score}!' if new_record_set else f'HIGH SCORE: {high_score}'
                game_over_surf = render_score(res_text, res_color)
                
                if score > high_score:
                    high_score = score
                    with open('highscore.txt', 'w') as f:
                        f.write(str(high_score))

        pipe_group.update(dt, current_scroll_speed)

        # Spawning
        pipe_timer += dt
        if pipe_timer > current_pipe_freq:
            h = random.randint(-100, 100)
            r_offset = random.uniform(0, math.pi * 2)
            r_freq = random.uniform(0.8, 1.2)
            pipe_group.add(Pipe(SCREEN_WIDTH, int(SCREEN_HEIGHT/2)+h, -1, pipe_img, pipe_mask, current_pipe_gap, pipe_move_speed, r_offset, r_freq))
            pipe_group.add(Pipe(SCREEN_WIDTH, int(SCREEN_HEIGHT/2)+h, 1, pipe_img_flipped, pipe_mask_flipped, current_pipe_gap, pipe_move_speed, r_offset, r_freq))
            pipe_timer = 0

    # Scrolling (Active in MENU and PLAYING)
    if game_state != STATE_GAMEOVER:
        ground_scroll -= current_scroll_speed * dt
        if abs(ground_scroll) > 35: ground_scroll = 0
        
        bg_scroll -= current_bg_speed * dt
        if abs(bg_scroll) > SCREEN_WIDTH: bg_scroll = 0

        bg_long_scroll -= (current_bg_speed / 2) * dt
        if abs(bg_long_scroll) > 1280: bg_long_scroll = 0

    # UI
    if game_state != STATE_MENU:
        if score_scale > 1.0:
            score_scale -= 2.0 * dt
            if score_scale < 1.0: score_scale = 1.0
            
            scaled_w = int(score_surface.get_width() * score_scale)
            scaled_h = int(score_surface.get_height() * score_scale)
            scaled_score = pygame.transform.scale(score_surface, (scaled_w, scaled_h))
            scaled_rect = scaled_score.get_rect(center=(SCREEN_WIDTH // 2, 50))
            render_surface.blit(scaled_score, scaled_rect)
        else:
            render_surface.blit(score_surface, score_rect)

    if game_state == STATE_MENU:
        pulse_scale = 1.0 + 0.05 * math.sin(pygame.time.get_ticks() * 0.005)
        w, h = menu_text_surf.get_size()
        scaled_menu = pygame.transform.scale(menu_text_surf, (int(w * pulse_scale), int(h * pulse_scale)))
        render_surface.blit(scaled_menu, scaled_menu.get_rect(center=(SCREEN_WIDTH // 2, 150)))

    if game_state == STATE_GAMEOVER:
        if game_over_surf:
            render_surface.blit(game_over_surf, game_over_surf.get_rect(center=(SCREEN_WIDTH // 2, 120)))

        if restart_delay > 0:
            button.draw(render_surface, True)
            restart_delay -= 1
            if restart_delay == 0:
                reset_game()
                swoosh_fx.play()
        elif button.draw(render_surface):
            reset_game()
            swoosh_fx.play()

    if flash_alpha > 0:
        flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        flash_surf.fill(WHITE)
        flash_surf.set_alpha(flash_alpha)
        render_surface.blit(flash_surf, (0, 0))
        flash_alpha -= 1500 * dt
        if flash_alpha < 0: flash_alpha = 0

    screen.fill(BLACK)
    screen.blit(render_surface, (offset_x, offset_y))

    for event in event_list:
        if event.type == QUIT:
            run = False
        if event.type == KEYDOWN:
            if event.key == K_SPACE:
                if game_state == STATE_MENU:
                    game_state = STATE_PLAYING
                    swoosh_fx.play()
                    pygame.mixer.music.play(-1)
                
                if game_state == STATE_PLAYING:
                    flappy.vel = JUMP_STRENGTH
                    flap_fx.play()
                
                elif game_state == STATE_GAMEOVER and restart_delay == 0:
                    restart_delay = 10

    pygame.display.flip()

pygame.quit()