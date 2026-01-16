import pygame
import random
from pygame.locals import *

pygame.init()

clock = pygame.time.Clock()
fps = 60

screen_width = 864
screen_height = 936

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Flappy Bird")

# define font
font = pygame.font.SysFont('PixelifySans', 60)
font.set_bold(True)

# define color
white = (255, 255, 255)

# game variables
ground_scroll = 0
scroll_speed = 4
start = False
game_over = False
pipe_gap = 150
pipe_freq = 1500  # ms
last_pipe = pygame.time.get_ticks() - pipe_freq
score = 0
pass_pipe = False

# load_images
bg = pygame.image.load('img/bg.png')
ground = pygame.image.load('img/ground.png')
button = pygame.image.load('img/restart.png')


def draw_text(text, font, text_color, x, y):
    img = font.render(text, True, text_color)
    screen.blit(img, (x, y))


def reset_game():
    pipe_group.empty()
    flappy.rect.x = 100
    flappy.rect.y = int(screen_height / 2)
    flappy.vel = 0
    score = 0
    global start
    start = False
    return score


class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.images = []
        self.index = 0
        self.counter = 0
        for num in range(1, 4):
            img = pygame.image.load(f'img/bird{num}.png')
            self.images.append(img)
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        self.vel = 0

    def update(self):

        # gravity
        if start == True:
            self.vel += 0.5
            if self.vel > 8:
                self.vel = 8
            if self.rect.bottom < 768:
                self.rect.y += int(self.vel)

        if game_over == False:
            # animation
            self.counter += 1
            flap_cooldown = 10

            if self.counter > flap_cooldown:
                self.counter = 0
                self.index += 1
                if self.index >= len(self.images):
                    self.index = 0
            self.image = self.images[self.index]

            # jump
            for event in event_list:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.vel = -10

            # rotate the bird
            self.image = pygame.transform.rotate(
                self.images[self.index], self.vel * -2)
        else:
            self.image = pygame.transform.rotate(
                self.images[self.index], -90)


class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load('img/pipe.png')
        self.rect = self.image.get_rect()
        # pipe position
        if position == 1:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect.bottomleft = [x, y - int(pipe_gap / 2)]
        if position == -1:
            self.rect.topleft = [x, y + int(pipe_gap / 2)]

    def update(self):
        self.rect.x -= scroll_speed
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

    def draw(self):

        reset = False

        # mouse position
        position = pygame.mouse.get_pos()

        # check if mouse is over the button
        if self.rect.collidepoint(position):
            screen.blit(self.hover_image, self.hover_rect)
            if pygame.mouse.get_pressed()[0] == 1:
                reset = True
        else:
            screen.blit(self.original_image, self.rect)

        return reset


bird_group = pygame.sprite.Group()
pipe_group = pygame.sprite.Group()

flappy = Bird(100, int(screen_height / 2))
bird_group.add(flappy)

# restart game
button = Button(screen_width // 2 - 50, screen_height // 2 - 100, button)

run = True
while run:

    event_list = pygame.event.get()

    clock.tick(fps)

    # background
    screen.blit(bg, (0, 0))

    bird_group.draw(screen)
    bird_group.update()
    pipe_group.draw(screen)

    # draw ground
    screen.blit(ground, (ground_scroll, 768))

    # check score
    if len(pipe_group) > 0:
        if bird_group.sprites()[0].rect.left > pipe_group.sprites()[0].rect.left and bird_group.sprites()[0].rect.right < pipe_group.sprites()[0].rect.right and pass_pipe == False:
            pass_pipe = True
        if pass_pipe == True:
            if bird_group.sprites()[0].rect.left > pipe_group.sprites()[0].rect.right:
                score += 1
                pass_pipe = False

    draw_text(str(score), font, white, int(screen_width / 2), 20)

    # ground collision check
    if flappy.rect.bottom >= 768:
        game_over = True

    # pipe collision check
    if pygame.sprite.groupcollide(bird_group, pipe_group, False, False) or flappy.rect.top < 0:
        game_over = True

    # draw and scroll the ground
    if game_over == False and start == True:
        # scroll ground
        ground_scroll -= scroll_speed
        if abs(ground_scroll) > 35:
            ground_scroll = 0
        pipe_group.update()

        # new pipes
        time_now = pygame.time.get_ticks()
        if time_now - last_pipe > pipe_freq:
            pipe_height = random.randint(-100, 100)
            btm_pipe = Pipe(screen_width, int(
                screen_height / 2) + pipe_height, -1)
            top_pipe = Pipe(screen_width, int(
                screen_height / 2) + pipe_height, 1)
            pipe_group.add(btm_pipe)
            pipe_group.add(top_pipe)
            last_pipe = time_now

    # Check game over
    if game_over == True:
        if button.draw() == True:
            game_over = False
            score = reset_game()

    for event in event_list:
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN and start == False and game_over == False:
            if event.key == pygame.K_SPACE:
                start = True

    pygame.display.update()

pygame.quit()
