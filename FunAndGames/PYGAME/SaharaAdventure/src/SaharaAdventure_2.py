import pygame
import sys
import random
import os

# === Setup ===
pygame.init()
WIDTH, HEIGHT = 800, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sahara Adventure – 2.5D")
clock = pygame.time.Clock()
FPS = 60

# === Asset Paths ===
ASSET_DIR = "sahara_assets"
def load_img(name):
    return pygame.image.load(os.path.join(ASSET_DIR, name)).convert_alpha()

# === Load Images ===
jeep_img = load_img("jeep.png")
dust_img = load_img("dust.png")
rock_img = load_img("rock.png")
cactus_img = load_img("cactus.png")
minimap_bg = load_img("minimap_bg.png")
minimap_icon = load_img("minimap_icon.png")

# === Game Settings ===
PLAYER_MIN_Y = 160
PLAYER_MAX_Y = HEIGHT - 60
OBSTACLE_LIST = []
DUST_CLOUDS = []

# === Classes ===

class Dust:
    def __init__(self, x, y, scale):
        self.image = pygame.transform.scale(dust_img, (int(30*scale), int(30*scale)))
        self.rect = self.image.get_rect(center=(x, y))
        self.alpha = 180
    def update(self):
        self.alpha -= 5
        self.image.set_alpha(self.alpha)
        return self.alpha > 0
    def draw(self, surface, scroll_x):
        surface.blit(self.image, (self.rect.x - scroll_x, self.rect.y))

class Obstacle:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.img = rock_img if kind == "rock" else cactus_img
        self.scale = 1.0 - ((self.y - PLAYER_MIN_Y) / (PLAYER_MAX_Y - PLAYER_MIN_Y)) * 0.4
        w = int(self.img.get_width() * self.scale)
        h = int(self.img.get_height() * self.scale)
        self.img_scaled = pygame.transform.scale(self.img, (w, h))
        self.rect = pygame.Rect(self.x, self.y - h, w, h)
    def draw(self, surface, scroll_x):
        surface.blit(self.img_scaled, (self.rect.x - scroll_x, self.rect.y))

class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.speed = 4
        self.width = jeep_img.get_width()
        self.height = jeep_img.get_height()
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def move(self, keys):
        vel_x, vel_y = 0, 0
        if keys[pygame.K_LEFT]:
            vel_x = -self.speed
        if keys[pygame.K_RIGHT]:
            vel_x = self.speed
        if keys[pygame.K_UP]:
            vel_y = -self.speed
        if keys[pygame.K_DOWN]:
            vel_y = self.speed
        if vel_x != 0 or vel_y != 0:
            scale = self.get_scale()
            DUST_CLOUDS.append(Dust(self.x, self.y, scale))
        self.x += vel_x
        self.y += vel_y
        self.y = max(PLAYER_MIN_Y, min(PLAYER_MAX_Y, self.y))

    def get_scale(self):
        return 1.0 - ((self.y - PLAYER_MIN_Y) / (PLAYER_MAX_Y - PLAYER_MIN_Y)) * 0.4

    def get_scaled_sprite(self):
        scale = self.get_scale()
        jeep_scaled = pygame.transform.scale(jeep_img, (int(self.width * scale), int(self.height * scale)))
        return jeep_scaled

    def draw(self, surface, scroll_x):
        jeep_scaled = self.get_scaled_sprite()
        jeep_rect = jeep_scaled.get_rect(midbottom=(self.x - scroll_x, self.y))
        self.rect = jeep_rect
        surface.blit(jeep_scaled, jeep_rect.topleft)

# === Draw Functions ===

def draw_ground(surface):
    surface.fill((255, 244, 214))  # sky
    pygame.draw.rect(surface, (237, 201, 175), (0, HEIGHT // 3, WIDTH, HEIGHT))  # sand
    for i in range(5):
        y = HEIGHT // 3 + i * 60
        pygame.draw.line(surface, (220, 190, 160), (WIDTH // 3, y), (WIDTH * 2 // 3, y), 2)

def draw_minimap(surface, player_x):
    mini = minimap_bg.copy()
    player_pos = int((player_x / 3000.0) * 60)
    mini.blit(minimap_icon, (player_pos, 28))
    surface.blit(mini, (WIDTH - 80, 20))

# === Game Setup ===

player = Player()
scroll_x = 0

# Generate obstacles
for i in range(25):
    x = random.randint(500, 3000)
    y = random.randint(PLAYER_MIN_Y, PLAYER_MAX_Y)
    kind = random.choice(["rock", "cactus"])
    OBSTACLE_LIST.append(Obstacle(x, y, kind))

# === Game Loop ===

running = True
while running:
    clock.tick(FPS)
    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    player.move(keys)
    scroll_x = player.x - WIDTH // 2

    # === Draw Scene ===
    draw_ground(screen)

    # Draw and update dust clouds
    DUST_CLOUDS[:] = [d for d in DUST_CLOUDS if d.update()]
    for d in DUST_CLOUDS:
        d.draw(screen, scroll_x)

    # Draw obstacles
    sorted_obstacles = sorted(OBSTACLE_LIST, key=lambda ob: ob.y)
    for ob in sorted_obstacles:
        ob.draw(screen, scroll_x)

    # Check collision (depth-aware)
    for ob in sorted_obstacles:
        if abs(ob.y - player.y) < 30 and player.rect.colliderect(ob.rect.move(-scroll_x, 0)):
            print("💥 Collision with", ob.kind)

    player.draw(screen, scroll_x)
    draw_minimap(screen, player.x)

    pygame.display.flip()

pygame.quit()
sys.exit()
