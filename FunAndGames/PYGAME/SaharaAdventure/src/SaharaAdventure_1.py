# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/SaharaAdventure_1.py
# ----------------------------

import pygame
import sys

# === Initialization ===
pygame.init()
WIDTH, HEIGHT = 800, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Safari Side Scroller")

clock = pygame.time.Clock()
FPS = 60

# === Colors ===
SAND = (237, 201, 175)
SKY = (255, 244, 214)
JEEP_COLOR = (66, 66, 66)
WHEEL_COLOR = (30, 30, 30)

# === Jeep Player Class ===
class Jeep:
    def __init__(self):
        self.width = 80
        self.height = 40
        self.x = 100
        self.y = HEIGHT - self.height - 40
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = True

    def move(self, keys):
        self.vel_x = 0
        if keys[pygame.K_LEFT]:
            self.vel_x = -5
        if keys[pygame.K_RIGHT]:
            self.vel_x = 5
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -15
            self.on_ground = False

        self.x += self.vel_x

    def apply_gravity(self):
        self.vel_y += 1  # gravity
        self.y += self.vel_y

        if self.y >= HEIGHT - self.height - 40:
            self.y = HEIGHT - self.height - 40
            self.vel_y = 0
            self.on_ground = True

    def draw(self, surface, offset):
        # Jeep body
        body_rect = pygame.Rect(self.x - offset, self.y, self.width, self.height)
        pygame.draw.rect(surface, JEEP_COLOR, body_rect)

        # Wheels
        pygame.draw.circle(surface, WHEEL_COLOR, (self.x - offset + 15, self.y + self.height), 10)
        pygame.draw.circle(surface, WHEEL_COLOR, (self.x - offset + 65, self.y + self.height), 10)

# === Environment ===
ground_y = HEIGHT - 40
background_scroll = 0

# === Platform terrain (simple hills/dunes) ===
dunes = [(i * 200, 30 * (i % 3)) for i in range(20)]

# === Game Setup ===
player = Jeep()

# === Game Loop ===
running = True
while running:
    clock.tick(FPS)
    screen.fill(SKY)

    # === Input ===
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    player.move(keys)
    player.apply_gravity()

    # === Scroll the background ===
    scroll_x = player.x - WIDTH // 2
    background_scroll = max(0, scroll_x)

    # === Draw Desert Ground ===
    pygame.draw.rect(screen, SAND, (0, ground_y, WIDTH, 40))

    # === Draw Dunes ===
    for dune_x, dune_h in dunes:
        dune_rect = pygame.Rect(dune_x - background_scroll, ground_y - dune_h, 200, dune_h)
        pygame.draw.rect(screen, (210, 180, 140), dune_rect)

    # === Draw Player Jeep ===
    player.draw(screen, background_scroll)

    # === Update Display ===
    pygame.display.flip()

pygame.quit()
sys.exit()
