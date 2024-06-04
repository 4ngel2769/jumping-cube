import pygame
import random
import os
import sys
import json
from pygame.locals import *

# Initialize Pygame
pygame.init()

# Global variable to store the start time of the game
game_start_ticks = 0

# Screen dimensions
screen_width = 800
screen_height = 600
border_thickness = 5

# Colors
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255)]
background_color = (100, 255, 100)
coin_color = (255, 223, 0)
menu_background_color = (42, 56, 82)
menu_text_color = (255, 255, 255)
menu_highlight_color = (60, 158, 250)
title_color = (255, 255, 0)

# Directories for save files
save_directory = os.path.join(os.path.expanduser("~"), "Documents", "JumpingCube", "saves")
if not os.path.exists(save_directory):
    os.makedirs(save_directory)

# Create screen
screen = pygame.display.set_mode((screen_width, screen_height), RESIZABLE)
pygame.display.set_caption('Jumping Square')

# Get the directory path of the script
# script_dir = os.path.dirname(sys.argv[0])

def get_asset_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # If running as a PyInstaller bundle, use _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # If running as a regular Python script, use relative path
        return os.path.join(os.path.abspath('.'), relative_path)

background_image_path = get_asset_path('background.jpeg')
platform_image_path = get_asset_path('platforms.png')
square_image_path = get_asset_path('square.png')

# # Load images
# background_image_path = os.path.join(script_dir, 'background.jpeg')
# platform_image_path = os.path.join(script_dir, 'platforms.png')
# square_image_path = os.path.join(script_dir, 'square.png')

background_image = pygame.image.load(background_image_path).convert()
platform_image = pygame.image.load(platform_image_path).convert_alpha()
square_image_original = pygame.image.load(square_image_path).convert_alpha()
square_image = pygame.transform.scale(square_image_original, (50, 50))

# Resize images
background_image = pygame.transform.scale(background_image, (screen_width, screen_height))
platform_image = pygame.transform.scale(platform_image, (100, 10))

# Square properties
square_size = 50
square_x = screen_width // 2 - square_size // 2
square_y = screen_height - square_size

# Jump properties
jump_speed = -15
gravity = 1
velocity_y = 0
is_jumping = False
double_jump = False
jumps_left = 0

# Movement properties
move_speed = 5

# Platform properties
platform_width = 100
platform_height = 10
num_platforms = 10
platforms = []

def generate_platforms():
    platforms.clear()
    max_x_distance = screen_width // 2
    max_y_distance = screen_height // 4
    min_y_distance = screen_height // 8  # Minimum vertical distance

    # Ensure at least two platforms are low enough
    min_platforms_low = 2
    low_platform_y_max = screen_height - 2 * (square_size + platform_height)

    low_platforms = []
    for _ in range(min_platforms_low):
        while True:
            platform_x = random.randint(0, screen_width - platform_width)
            platform_y = random.randint(screen_height // 2, low_platform_y_max)
            new_platform = pygame.Rect(platform_x, platform_y, platform_width, platform_height)
            if all(not new_platform.colliderect(existing) for existing in platforms):
                platforms.append(new_platform)
                low_platforms.append(new_platform)
                break

    # Ensure at least three platforms are within jumping distance from the low platforms
    min_high_platforms = 3
    high_platforms = 0

    for low_platform in low_platforms:
        for _ in range(min_high_platforms):
            while True:
                platform_x = random.randint(max(0, low_platform.x - max_x_distance), min(screen_width - platform_width, low_platform.x + max_x_distance))
                platform_y = random.randint(max(0, low_platform.y - max_y_distance), low_platform.y - min_y_distance)
                new_platform = pygame.Rect(platform_x, platform_y, platform_width, platform_height)
                if all(not new_platform.colliderect(existing) for existing in platforms):
                    platforms.append(new_platform)
                    high_platforms += 1
                    break

    # Generate the remaining platforms
    while len(platforms) < num_platforms:
        while True:
            platform_x = random.randint(0, screen_width - platform_width)
            platform_y = random.randint(0, screen_height - platform_height)
            new_platform = pygame.Rect(platform_x, platform_y, platform_width, platform_height)
            if all(not new_platform.colliderect(existing) for existing in platforms):
                if not platforms or (
                    abs(new_platform.x - platforms[-1].x) <= max_x_distance and
                    min_y_distance <= abs(new_platform.y - platforms[-1].y) <= max_y_distance
                ):
                    platforms.append(new_platform)
                    break

generate_platforms()

# Coin properties
coin_size = 20
coins = []
num_coins = 10
collected_coins = 0

def generate_coins():
    current_coins = len(coins)
    coins_needed = num_coins - current_coins
    min_distance = coin_size * 2  # Minimum distance between coins
    for _ in range(coins_needed):
        while True:
            coin_x = random.randint(0, screen_width - coin_size)
            coin_y = random.randint(0, screen_height - coin_size)
            new_coin = pygame.Rect(coin_x, coin_y, coin_size, coin_size)
            if all(abs(new_coin.x - existing.x) >= min_distance and abs(new_coin.y - existing.y) >= min_distance for existing in coins):
                coins.append(new_coin)
                break

generate_coins()

# Font for displaying coin count and timer
font = pygame.font.SysFont(None, 36)

# Ability Timer
ability_start_time = None
ability_duration = 10000  # 10 seconds

# Clock
clock = pygame.time.Clock()

def draw_platforms():
    for platform in platforms:
        screen.blit(platform_image, (platform.x, platform.y))

def draw_coins():
    for coin in coins:
        pygame.draw.rect(screen, coin_color, coin)

def draw_coin_count():
    text = font.render(f'Coins: {collected_coins}', True, (255, 255, 255))
    screen.blit(text, (10, 10))

def draw_ability_status():
    if ability_start_time and pygame.time.get_ticks() - game_start_ticks - ability_start_time < ability_duration:
        remaining_time = (ability_duration - (pygame.time.get_ticks() - game_start_ticks - ability_start_time)) // 1000
        text = font.render(f'Ability: Double Jump ({remaining_time}s)', True, (255, 255, 255))
        screen.blit(text, (screen_width - text.get_width() - 10, 10))

def draw_borders():
    if ability_start_time and pygame.time.get_ticks() - ability_start_time < ability_duration:
        border_color = random.choice(colors)
    else:
        border_color = (255, 255, 255)

    pygame.draw.rect(screen, border_color, (0, 0, screen_width, border_thickness))
    pygame.draw.rect(screen, border_color, (0, 0, border_thickness, screen_height))
    pygame.draw.rect(screen, border_color, (0, screen_height - border_thickness, screen_width, border_thickness))
    pygame.draw.rect(screen, border_color, (screen_width - border_thickness, 0, border_thickness, screen_height))

def check_collision(rect1, rect2):
    return rect1.colliderect(rect2)

def draw_button(text, x, y, width, height, action=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()

    if x + width > mouse[0] > x and y + height > mouse[1] > y:
        pygame.draw.rect(screen, menu_highlight_color, (x, y, width, height))
        if click[0] == 1 and action is not None:
            action()
    else:
        pygame.draw.rect(screen, menu_text_color, (x, y, width, height))

    button_text = font.render(text, True, menu_background_color)
    screen.blit(button_text, (x + (width - button_text.get_width()) // 2, y + (height - button_text.get_height()) // 2))

def start_game():
    global game_active, game_time, square_x, square_y, collected_coins, double_jump, ability_start_time
    game_active = True
    game_time = pygame.time.get_ticks()
    square_x = screen_width // 2 - square_size // 2
    square_y = screen_height - square_size
    collected_coins = 0
    double_jump = False
    ability_start_time = None
    generate_platforms()
    generate_coins()

def quit_game():
    global running
    running = False

def go_to_main_menu():
    global game_active, paused, username_menu, load_game_menu, save_prompt, new_save_prompt, running
    game_active = False
    paused = False
    username_menu = False
    load_game_menu = False
    save_prompt = False
    new_save_prompt = False
    # Redraw the main menu
    draw_main_menu()

def draw_main_menu():
    screen.fill(menu_background_color)
    title = font.render("Jumping Square", True, title_color)
    screen.blit(title, (screen_width // 2 - title.get_width() // 2, screen_height // 4))
    draw_button("New Game", screen_width // 2 - 100, screen_height // 2 - 50, 200, 50, start_game)
    if os.path.exists(os.path.join(save_directory, f'save_{username_input}.json')):
        draw_button("Load Game", screen_width // 2 - 100, screen_height // 2 + 50, 200, 50, load_game_prompt)
    else:
        draw_button("Load Game", screen_width // 2 - 100, screen_height // 2 + 50, 200, 50)
    draw_button("Quit", screen_width // 2 - 100, screen_height // 2 + 150, 200, 50, quit_game)
    pygame.display.flip()

def draw_pause_menu():
    screen.fill(menu_background_color)
    draw_button("Resume", screen_width // 2 - 100, screen_height // 2 - 50, 200, 50, resume_game)
    draw_button("Save and Main Menu", screen_width // 2 - 100, screen_height // 2 + 50, 200, 50, save_and_main_menu)
    draw_button("Main Menu", screen_width // 2 - 100, screen_height // 2 + 150, 200, 50, go_to_main_menu)
    pygame.display.flip()

def draw_username_menu():
    screen.fill(menu_background_color)
    prompt_text = font.render("Enter your username:", True, menu_text_color)
    username_text = font.render(username_input, True, menu_text_color)
    screen.blit(prompt_text, (screen_width // 2 - prompt_text.get_width() // 2, screen_height // 3))
    screen.blit(username_text, (screen_width // 2 - username_text.get_width() // 2, screen_height // 2))
    pygame.display.flip()

def draw_save_prompt():
    screen.fill(menu_background_color)
    title_text = font.render("Save Game", True, title_color)
    screen.blit(title_text, (screen_width // 2 - title_text.get_width() // 2, screen_height // 4))
    prompt_text = font.render(f'Save file exists for {username_input}. Overwrite?', True, menu_text_color)
    screen.blit(prompt_text, (screen_width // 2 - prompt_text.get_width() // 2, screen_height // 3))
    draw_button("Yes", screen_width // 2 - 100, screen_height // 2 - 50, 200, 50, overwrite_save)
    draw_button("No", screen_width // 2 - 100, screen_height // 2 + 50, 200, 50, go_back_to_pause_menu)
    pygame.display.flip()

def go_back_to_pause_menu():
    global save_prompt
    save_prompt = False
    paused = True


def draw_create_new_save_prompt():
    screen.fill(menu_background_color)
    prompt_text = font.render(f'Enter new save name for {username_input}:', True, menu_text_color)
    new_save_text = font.render(new_save_input, True, menu_text_color)
    screen.blit(prompt_text, (screen_width // 2 - prompt_text.get_width() // 2, screen_height // 3))
    screen.blit(new_save_text, (screen_width // 2 - new_save_text.get_width() // 2, screen_height // 2))
    pygame.display.flip()

def save_game(username):
    save_data = {
        'username': username,
        'collected_coins': collected_coins,
        'square_x': square_x,
        'square_y': square_y,
        'platforms': [(platform.x, platform.y) for platform in platforms],
        'coins': [(coin.x, coin.y) for coin in coins],
        'double_jump': double_jump,
        'ability_start_time': ability_start_time,
        'game_time': pygame.time.get_ticks()
    }
    save_path = os.path.join(save_directory, f'save_{username}.json')
    if os.path.exists(save_path):
        global save_prompt, current_save_data
        save_prompt = True
        current_save_data = save_data  # Store save data to be used in prompt
        return False  # Indicates that we need to show the save prompt
    with open(save_path, 'w') as save_file:
        json.dump(save_data, save_file)
    return True

def load_game(username):
    global collected_coins, square_x, square_y, platforms, coins, double_jump, ability_start_time, game_active, game_start_ticks
    save_path = os.path.join(save_directory, f'save_{username}.json')
    if os.path.exists(save_path):
        with open(save_path, 'r') as save_file:
            save_data = json.load(save_file)
            collected_coins = save_data['collected_coins']
            square_x = save_data['square_x']
            square_y = save_data['square_y']
            platforms = [pygame.Rect(x, y, platform_width, platform_height) for x, y in save_data['platforms']]
            coins = [pygame.Rect(x, y, coin_size, coin_size) for x, y in save_data['coins']]
            double_jump = save_data['double_jump']
            ability_start_time = save_data['ability_start_time']
            game_start_ticks = pygame.time.get_ticks() - save_data['game_time']
        game_active = True

def resume_game():
    global paused
    paused = False

def save_and_main_menu():
    if not save_game(username_input):
        global save_prompt
        save_prompt = True
    else:
        go_to_main_menu()

def overwrite_save():
    save_path = os.path.join(save_directory, f'save_{username_input}.json')
    with open(save_path, 'w') as save_file:
        json.dump(current_save_data, save_file)
    save_prompt = False
    go_to_main_menu()

def create_new_save_prompt():
    global new_save_prompt
    new_save_prompt = True

def create_new_save():
    save_num = 1
    while os.path.exists(os.path.join(save_directory, f'save_{new_save_input}_{save_num}.json')):
        save_num += 1
    save_path = os.path.join(save_directory, f'save_{new_save_input}_{save_num}.json')
    with open(save_path, 'w') as save_file:
        json.dump(current_save_data, save_file)
    save_prompt = False
    new_save_prompt = False
    go_to_main_menu()

def load_game_prompt():
    global load_game_menu
    load_game_menu = True

def draw_load_game_menu():
    screen.fill(menu_background_color)
    prompt_text = font.render(f'Select save file for {username_input}:', True, menu_text_color)
    screen.blit(prompt_text, (screen_width // 2 - prompt_text.get_width() // 2, screen_height // 4))
    
    save_files = [f for f in os.listdir(save_directory) if f.startswith(f'save_{username_input}')]
    for i, save_file in enumerate(save_files):
        draw_button(save_file, screen_width // 2 - 150, screen_height // 2 - 50 + i * 60, 300, 50, lambda f=save_file: load_game(f.split('_')[1].split('.')[0]))

    pygame.display.flip()

# Main loop
running = True
game_active = False
paused = False
username_menu = True
username_input = ""
save_prompt = False
new_save_prompt = False
load_game_menu = False
current_save_data = {}
new_save_input = ""

while running:
    if username_menu:
        draw_username_menu()
    elif save_prompt:
        draw_save_prompt()
    elif new_save_prompt:
        draw_create_new_save_prompt()
    elif load_game_menu:
        draw_load_game_menu()
    elif not game_active:
        draw_main_menu()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if username_menu:
                if event.key == pygame.K_RETURN and username_input:
                    username_menu = False
                elif event.key == pygame.K_BACKSPACE:
                    username_input = username_input[:-1]
                else:
                    username_input += event.unicode
            elif new_save_prompt:
                if event.key == pygame.K_RETURN and new_save_input:
                    create_new_save()
                elif event.key == pygame.K_BACKSPACE:
                    new_save_input = new_save_input[:-1]
                else:
                    new_save_input += event.unicode
            elif not game_active and not save_prompt:
                if event.key == pygame.K_s:
                    game_active = True
                    generate_platforms()
                    generate_coins()
                elif event.key == pygame.K_q:
                    running = False
            elif paused and not save_prompt:
                if event.key == pygame.K_r:
                    paused = False
                elif event.key == pygame.K_v:
                    if not save_game(username_input):
                        save_prompt = True
                elif event.key == pygame.K_q:
                    running = False
            else:
                if event.key == pygame.K_ESCAPE:
                    paused = True
                if event.key == pygame.K_SPACE and not is_jumping:
                    if double_jump and jumps_left > 0:
                        jumps_left -= 1
                        velocity_y = jump_speed
                    elif not is_jumping:
                        is_jumping = True
                        velocity_y = jump_speed

        if event.type == VIDEORESIZE:
            screen_width, screen_height = event.size
            screen = pygame.display.set_mode((screen_width, screen_height), RESIZABLE)
            background_image = pygame.transform.scale(background_image, (screen_width, screen_height))

        if event.type == ACTIVEEVENT and game_active:
            if event.state == 2 and not event.gain:
                paused = True

    if game_active and not paused and not save_prompt:
        # Get keys pressed
        keys = pygame.key.get_pressed()

        # Move left
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            square_x -= move_speed
        # Move right
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            square_x += move_speed

        # Ensure the square stays within screen bounds
        square_x = max(0, min(screen_width - square_size, square_x))

        square_rect = pygame.Rect(square_x, square_y, square_size, square_size)

        # Track if the square is in the air
        was_in_air = not is_jumping and velocity_y != 0

        # Apply gravity if the square is not on any platform
        on_platform = False
        for platform in platforms:
            if check_collision(square_rect, platform):
                if velocity_y > 0 and square_rect.bottom <= platform.bottom:
                    square_y = platform.top - square_size
                    velocity_y = 0
                    on_platform = True
                    is_jumping = False
                    jumps_left = 1 if double_jump else 0
                    break
                elif velocity_y < 0 and square_rect.top >= platform.top:
                    # Allow passing through from below
                    pass

        if not on_platform:
            velocity_y += gravity
            square_y += velocity_y
            if square_y >= screen_height - square_size:
                square_y = screen_height - square_size
                if was_in_air:  # Change color only if it was in the air
                    square_image = pygame.transform.scale(square_image_original, (50, 50))
                velocity_y = 0
                is_jumping = False
                jumps_left = 1 if double_jump else 0
        else:
            if was_in_air:  # Change color only if it was in the air
                square_image = pygame.transform.scale(square_image_original, (50, 50))

        # Check for coin collection
        for coin in coins[:]:
            if check_collision(square_rect, coin):
                coins.remove(coin)
                collected_coins += 1

                # Check for new ability
                if collected_coins % 5 == 0:
                    double_jump = True
                    ability_start_time = pygame.time.get_ticks()

                # Generate more coins if 50% collected
                if len(coins) < num_coins // 2:
                    generate_coins()

        # Draw everything
        screen.blit(background_image, (0, 0))
        screen.blit(square_image, (square_x, square_y))
        draw_platforms()
        draw_coins()
        draw_coin_count()
        draw_ability_status()
        draw_borders()
        pygame.display.flip()

    elif paused and not save_prompt:
        draw_pause_menu()

    # Cap the frame rate
    clock.tick(30)

pygame.quit()
