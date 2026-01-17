import pygame
import random
from pygame.locals import *

pygame.mixer.pre_init(48000, -16, 2, 4096)
pygame.init()

clock = pygame.time.Clock()
fps = 60

screen_width = 864
screen_height = 936

screen = pygame.display.set_mode((screen_width, screen_height))
render_surface = pygame.Surface((screen_width, screen_height))
pygame.display.set_caption("Flappy Bird")

# define font
font = pygame.font.Font('04B_19.ttf', 60)

# define color
white = (255, 255, 255)
black = (0, 0, 0)
red = (255, 0, 0)
blue = (30, 80, 250) # Lighter, vibrant blue
green = (0, 150, 0) # Dark Green
new_record_set = False

# game variables
ground_scroll = 0
bg_scroll = 0
scroll_speed = 240 # Pixels per second (4 * 60)
bg_scroll_speed = 60
start = False
game_over = False
pipe_gap = 150
pipe_freq = 1500  # ms
last_pipe = pygame.time.get_ticks() - pipe_freq
score = 0
pass_pipe = False
hit_played = False
die_played = False
shake_duration = 0
shake_intensity = 0

# Load high score
try:
    with open('highscore.txt', 'r') as f:
        high_score = int(f.read())
except:
    high_score = 0

# Cache for score rendering
def render_score(score_val, color=white):
    text = str(score_val)
    main_surf = font.render(text, True, color)
    shadow_surf = font.render(text, True, black)
    w, h = main_surf.get_size()
    surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    surf.blit(shadow_surf, (2, 2))
    surf.blit(main_surf, (0, 0))
    return surf

score_surface = render_score(score, white)
score_rect = score_surface.get_rect(center=(screen_width // 2, 50))

# load_images
bg = pygame.image.load('img/bg.png').convert()
ground = pygame.image.load('img/ground.png').convert()
button_img = pygame.image.load('img/restart.png').convert()
pipe_img = pygame.image.load('img/pipe.png').convert_alpha()
pipe_img_flipped = pygame.transform.flip(pipe_img, False, True)

# Pre-calculate masks
pipe_mask = pygame.mask.from_surface(pipe_img)
pipe_mask_flipped = pygame.mask.from_surface(pipe_img_flipped)

# load sounds
flap_fx = pygame.mixer.Sound('audio/sfx_wing.wav')
hit_fx = pygame.mixer.Sound('audio/sfx_hit.wav')
point_fx = pygame.mixer.Sound('audio/sfx_point.wav')
die_fx = pygame.mixer.Sound('audio/sfx_die.wav')
swoosh_fx = pygame.mixer.Sound('audio/sfx_swooshing.wav')

# load background music
pygame.mixer.music.load('audio/bg_music.mp3')
pygame.mixer.music.set_volume(0.5)


def reset_game():
    global score, score_surface, score_rect, start, hit_played, die_played, pass_pipe, last_pipe, new_record_set
    pipe_group.empty()
    flappy.rect.x = 100
    flappy.rect.y = screen_height / 2
    flappy.vel = 0
    score = 0
    score_surface = render_score(score, white)
    score_rect = score_surface.get_rect(center=(screen_width // 2, 50))
    pass_pipe = False
    last_pipe = pygame.time.get_ticks() - pipe_freq
    start = False
    hit_played = False
    die_played = False
    new_record_set = False
    global shake_duration, shake_intensity
    shake_duration = 0
    shake_intensity = 0
    return score
class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.images = []
        self.masks = [] # Store masks for each frame
        self.index = 0
        self.animation_timer = 0
        self.flap_speed = 0.1
        for num in range(1, 4):
            img = pygame.image.load(f'img/bird{num}.png').convert_alpha()
            self.images.append(img)
            self.masks.append(pygame.mask.from_surface(img))
        self.image = self.images[self.index]
        self.mask = self.masks[self.index]
        self.rect = self.image.get_frect()
        self.rect.center = [x, y]
        self.vel = 0
        self.rotation_cache = {}
        self.mask_cache = {} # Cache masks for rotated versions

    def update(self, dt):
        # gravity
        if start == True:
            self.vel += 30 * dt
            if self.vel > 15:
                self.vel = 15
            if self.rect.bottom < 768:
                self.rect.y += self.vel

        if game_over == False:
            # animation (time-based)
            self.animation_timer += dt
            if self.animation_timer > self.flap_speed:
                self.animation_timer = 0
                self.index = (self.index + 1) % len(self.images)
            
            # rotate the bird with caching
            angle = int(self.vel * -3)
            cache_key = (self.index, angle)
            if cache_key not in self.rotation_cache:
                rotated_img = pygame.transform.rotate(self.images[self.index], angle)
                self.rotation_cache[cache_key] = rotated_img
                self.mask_cache[cache_key] = pygame.mask.from_surface(rotated_img)
            
            self.image = self.rotation_cache[cache_key]
            self.mask = self.mask_cache[cache_key]
        else:
            self.image = pygame.transform.rotate(self.images[self.index], -90)
            self.mask = pygame.mask.from_surface(self.image)

class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position, image, mask):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.mask = mask
        self.rect = self.image.get_frect()
        # pipe position
        if position == 1:
            self.rect.bottomleft = [x, y - pipe_gap / 2]
        if position == -1:
            self.rect.topleft = [x, y + pipe_gap / 2]

    def update(self, dt):
        self.rect.x -= scroll_speed * dt
        if self.rect.right < 0:
            self.kill()


class Button():
    def __init__(self, x, y, image):
        self.original_image = image
        self.hover_image = pygame.transform.scale(
            image, (int(image.get_width() * 1.1), int(image.get_height() * 1.1)))
        self.rect = self.original_image.get_rect()
        self.rect.topleft = (x, y)
        self.hover_rect = self.hover_image.get_rect()
        self.hover_rect.center = self.rect.center

    def draw(self, surface, forced_pressed=False):

        reset = False

        # mouse position
        position = pygame.mouse.get_pos()

        # check if mouse is over the button or if pressed is forced
        if self.rect.collidepoint(position) or forced_pressed:
            surface.blit(self.hover_image, self.hover_rect)
            if pygame.mouse.get_pressed()[0] == 1:
                reset = True
        else:
            surface.blit(self.original_image, self.rect)

        return reset


bird_group = pygame.sprite.Group()
pipe_group = pygame.sprite.Group()

flappy = Bird(100, int(screen_height / 2))
bird_group.add(flappy)

# restart game
button = Button(screen_width // 2 - 50, screen_height // 2 - 100, button_img)

run = True
restart_delay = 0

while run:

    event_list = pygame.event.get()

    # Calculate delta time (dt) in seconds
    dt = clock.tick(fps) / 1000.0

    # Screen shake logic
    offset_x = 0
    offset_y = 0
    if shake_duration > 0:
        shake_duration -= dt
        offset_x = random.randint(-int(shake_intensity), int(shake_intensity))
        offset_y = random.randint(-int(shake_intensity), int(shake_intensity))

    # background
    render_surface.blit(bg, (bg_scroll, 0))
    render_surface.blit(bg, (bg_scroll + screen_width, 0))

    pipe_group.draw(render_surface)
    bird_group.draw(render_surface)
    bird_group.update(dt)

    # draw ground
    render_surface.blit(ground, (ground_scroll, 768))

    # game logic
    if game_over == False and start == True:
        # check score
        if len(pipe_group) > 0:
            if bird_group.sprites()[0].rect.left > pipe_group.sprites()[0].rect.left and bird_group.sprites()[0].rect.right < pipe_group.sprites()[0].rect.right and pass_pipe == False:
                pass_pipe = True
            if pass_pipe == True:
                if bird_group.sprites()[0].rect.left > pipe_group.sprites()[0].rect.right:
                    score += 1
                    if score > high_score:
                        new_record_set = True
                    color = red if new_record_set else white
                    score_surface = render_score(score, color)
                    score_rect = score_surface.get_rect(center=(screen_width // 2, 50))
                    pass_pipe = False
                    point_fx.play()

        # ground collision check
        if flappy.rect.bottom >= 768:
            game_over = True
            if die_played == False:
                die_fx.play()
                die_played = True
                shake_duration = 0.4
                shake_intensity = 15
                pygame.mixer.music.stop()
                if score > high_score:
                    high_score = score
                    with open('highscore.txt', 'w') as f:
                        f.write(str(high_score))

        # pipe collision check with masks
        if pygame.sprite.groupcollide(bird_group, pipe_group, False, False, pygame.sprite.collide_mask) or flappy.rect.top < 0:
            game_over = True
            if hit_played == False:
                hit_fx.play()
                hit_played = True
                shake_duration = 0.4
                shake_intensity = 15
                pygame.mixer.music.stop()
                if score > high_score:
                    high_score = score
                    with open('highscore.txt', 'w') as f:
                        f.write(str(high_score))

        # scroll ground
        ground_scroll -= scroll_speed * dt
        if abs(ground_scroll) > 35:
            ground_scroll = 0

        # scroll background (parallax)
        bg_scroll -= bg_scroll_speed * dt
        if abs(bg_scroll) > screen_width:
            bg_scroll = 0

        pipe_group.update(dt)

        # new pipes
        time_now = pygame.time.get_ticks()
        if time_now - last_pipe > pipe_freq:
            pipe_height = random.randint(-100, 100)
            btm_pipe = Pipe(screen_width, int(
                screen_height / 2) + pipe_height, -1, pipe_img, pipe_mask)
            top_pipe = Pipe(screen_width, int(
                screen_height / 2) + pipe_height, 1, pipe_img_flipped, pipe_mask_flipped)
            pipe_group.add(btm_pipe)
            pipe_group.add(top_pipe)
            last_pipe = time_now

    # Draw cached score
    render_surface.blit(score_surface, score_rect)

    # Check game over
    if game_over == True:
        if new_record_set:
            high_score_surf = render_score(f'NEW RECORD: {score}!', green)
        else:
            high_score_surf = render_score(f'HIGH SCORE: {high_score}', blue)
        high_score_rect = high_score_surf.get_rect(center=(screen_width // 2, 120))
        render_surface.blit(high_score_surf, high_score_rect)

        if restart_delay > 0:
            button.draw(render_surface, forced_pressed=True)
            restart_delay -= 1
            if restart_delay == 0:
                game_over = False
                score = reset_game()
                swoosh_fx.play()
        else:
            if button.draw(render_surface) == True:
                game_over = False
                score = reset_game()
                swoosh_fx.play()

    # Final blit to screen with shake offset
    screen.fill(black) # Fill with black to avoid ghosting
    screen.blit(render_surface, (offset_x, offset_y))

    for event in event_list:
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if start == False and game_over == False:
                    start = True
                    swoosh_fx.play()
                    pygame.mixer.music.play(-1)
                
                # Jump logic (only if game is active)
                if start == True and game_over == False:
                    flappy.vel = -8
                    flap_fx.play()
                
                if game_over == True and restart_delay == 0:
                    restart_delay = 10  # Show press effect for 10 frames

    pygame.display.flip()

pygame.quit()
