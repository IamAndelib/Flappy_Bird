import pygame
import random
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
current_pipe_gap = PIPE_GAP
current_pipe_freq = PIPE_FREQ
score = 0
pass_pipe = False
hit_played = False
die_played = False
shake_duration = 0
flash_alpha = 0
new_record_set = False
score_scale = 1.0

# Load high score
try:
    with open('highscore.txt', 'r') as f:
        high_score = int(f.read())
except:
    high_score = 0

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

score_surface = render_score(score, WHITE)
score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))

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
    size = image.get_size()
    shrunk_size = (int(size[0] * factor), int(size[1] * factor))
    if shrunk_size[0] <= 0 or shrunk_size[1] <= 0:
        return pygame.mask.from_surface(image)
    shrunk_img = pygame.transform.smoothscale(image, shrunk_size)
    shrunk_mask = pygame.mask.from_surface(shrunk_img)
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
    pipe_group.empty()
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
    game_state = STATE_MENU
    hit_played = False
    die_played = False
    new_record_set = False
    shake_duration = 0
    flash_alpha = 0
    return score

class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.images = BIRD_IMAGES
        self.masks = BIRD_MASKS
        self.index = 0
        self.animation_timer = 0
        
        self.image = self.images[self.index]
        self.mask = self.masks[self.index]
        self.rect = self.image.get_frect()
        self.rect.center = [x, y]
        self.vel = 0
        self.rotation_cache = {}
        self.mask_cache = {}

    def update(self, dt):
        if game_state != STATE_MENU:
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
            self.image = pygame.transform.rotate(self.images[self.index], -90)
            self.mask = pygame.mask.from_surface(self.image)

class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position, image, mask, gap):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.mask = mask
        self.rect = self.image.get_frect()
        if position == 1:
            self.rect.bottomleft = [x, y - gap / 2]
        if position == -1:
            self.rect.topleft = [x, y + gap / 2]

    def update(self, dt, speed):
        self.rect.x -= speed * dt
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

# --- Instantiate Objects ---
bird_group = pygame.sprite.GroupSingle()
flappy = Bird(100, int(SCREEN_HEIGHT / 2))
bird_group.add(flappy)
pipe_group = pygame.sprite.Group()
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
    bird_group.draw(render_surface)
    bird_group.update(dt)

    render_surface.blit(ground, (ground_scroll, GROUND_LEVEL))

    # Logic
    if game_state == STATE_PLAYING:
        run_timer += dt
        
        # Difficulty scaling (gradually over 300 seconds, slowing down as it gets harder)
        # Using square root ensures the rate of increase decreases over time
        scale = min((run_timer / 300.0) ** 0.5, 1.0)
        current_scroll_speed = SCROLL_SPEED + (scale * 160)  # Max 400
        current_pipe_gap = PIPE_GAP - (scale * 50)          # Min 100
        current_pipe_freq = PIPE_FREQ - (scale * 0.7)        # Min 0.8
        current_bg_speed = current_scroll_speed / 4

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
                    score_scale = 1.4  # Trigger pop effect

        # Collisions
        pipe_hit = pygame.sprite.spritecollide(flappy, pipe_group, False, pygame.sprite.collide_mask)
        if flappy.rect.bottom >= GROUND_LEVEL or flappy.rect.top < 0 or pipe_hit:
            
            game_state = STATE_GAMEOVER
            if not hit_played:
                shake_duration = SHAKE_DURATION
                flash_alpha = 255
                if flappy.rect.bottom < GROUND_LEVEL:
                    hit_fx.play()
                    if pipe_hit:
                        swoosh_fx.play()
                die_fx.play()
                hit_played = True
                pygame.mixer.music.stop()
                if score > high_score:
                    high_score = score
                    with open('highscore.txt', 'w') as f:
                        f.write(str(high_score))

        # Scrolling
        ground_scroll -= current_scroll_speed * dt
        if abs(ground_scroll) > 35: ground_scroll = 0
        
        bg_scroll -= current_bg_speed * dt
        if abs(bg_scroll) > SCREEN_WIDTH: bg_scroll = 0

        bg_long_scroll -= (current_bg_speed / 2) * dt
        if abs(bg_long_scroll) > 1280: bg_long_scroll = 0

        pipe_group.update(dt, current_scroll_speed)

        # Spawning
        pipe_timer += dt
        if pipe_timer > current_pipe_freq:
            h = random.randint(-100, 100)
            pipe_group.add(Pipe(SCREEN_WIDTH, int(SCREEN_HEIGHT/2)+h, -1, pipe_img, pipe_mask, current_pipe_gap))
            pipe_group.add(Pipe(SCREEN_WIDTH, int(SCREEN_HEIGHT/2)+h, 1, pipe_img_flipped, pipe_mask_flipped, current_pipe_gap))
            pipe_timer = 0

    # UI
    if game_state != STATE_MENU:
        if score_scale > 1.0:
            score_scale -= 2.0 * dt  # Smoothly return to normal size
            if score_scale < 1.0: score_scale = 1.0
            
            scaled_w = int(score_surface.get_width() * score_scale)
            scaled_h = int(score_surface.get_height() * score_scale)
            scaled_score = pygame.transform.smoothscale(score_surface, (scaled_w, scaled_h))
            scaled_rect = scaled_score.get_rect(center=(SCREEN_WIDTH // 2, 50))
            render_surface.blit(scaled_score, scaled_rect)
        else:
            render_surface.blit(score_surface, score_rect)

    if game_state == STATE_MENU:
        menu_text = render_score("PRESS SPACE TO FLAP", ORANGE)
        render_surface.blit(menu_text, menu_text.get_rect(center=(SCREEN_WIDTH // 2, 150)))

    if game_state == STATE_GAMEOVER:
        res_color = GREEN if new_record_set else BLUE
        res_text = f'NEW RECORD: {score}!' if new_record_set else f'HIGH SCORE: {high_score}'
        high_score_surf = render_score(res_text, res_color)
        render_surface.blit(high_score_surf, high_score_surf.get_rect(center=(SCREEN_WIDTH // 2, 120)))

        if restart_delay > 0:
            button.draw(render_surface, True)
            restart_delay -= 1
            if restart_delay == 0:
                reset_game()
                swoosh_fx.play()
        elif button.draw(render_surface):
            reset_game()
            swoosh_fx.play()

    # Smooth Flash Fade-out
    if flash_alpha > 0:
        flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        flash_surf.fill(WHITE)
        flash_surf.set_alpha(flash_alpha)
        render_surface.blit(flash_surf, (0, 0))
        flash_alpha -= 1500 * dt # Fade out quickly
        if flash_alpha < 0: flash_alpha = 0

    # Output
    screen.fill(BLACK)
    screen.blit(render_surface, (offset_x, offset_y))

    for event in event_list:
        if event.type == QUIT:
            with open('highscore.txt', 'w') as f:
                f.write('0')
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
                
                if game_state == STATE_GAMEOVER and restart_delay == 0:
                    restart_delay = 10

    pygame.display.flip()

pygame.quit()
