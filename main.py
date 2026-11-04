import pygame

from game.world import World
from game.agent import Agent
from game.game_manager import GameManager
from game.i18n import get_language, set_language
from ui.renderer import Renderer, WINDOW_SIZE
from ui.controls import ControlPanel
from ui.dev_panel import DevPanel
from ui.sound_manager import SoundManager

ARROW_KEYS = {
    pygame.K_UP: "UP",
    pygame.K_DOWN: "DOWN",
    pygame.K_LEFT: "LEFT",
    pygame.K_RIGHT: "RIGHT",
}
MOVES = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


def handle_key(key, gm, renderer, dev_panel=None):
    """Keyboard shortcuts mirror the on-screen controls."""
    if key == pygame.K_F1 and dev_panel:
        dev_panel.toggle()
    elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
        gm.set_play_mode(gm.PLAY_MODES[key - pygame.K_1])
    elif key == pygame.K_SPACE:
        gm.set_play_mode("step")
        gm.step_ai()
    elif key == pygame.K_a:
        gm.auto_mode = not gm.auto_mode
    elif key == pygame.K_r:
        gm.reset(mode="replay")
    elif key == pygame.K_m:
        gm.reset(mode="random")
    elif key == pygame.K_d:
        gm.reset(mode="classic")
    elif key == pygame.K_TAB:
        renderer.reveal_all = not renderer.reveal_all
    elif key == pygame.K_t:
        renderer.set_dark(not renderer.dark)
    elif key == pygame.K_l:
        set_language("ko" if get_language() == "en" else "en")
    elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
        gm.set_num_rooms(gm.num_rooms + 1)
    elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
        gm.set_num_rooms(gm.num_rooms - 1)
    elif key in ARROW_KEYS:
        direction = ARROW_KEYS[key]
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            gm.manual_shoot(direction)
        else:
            gm.manual_move(*MOVES[direction])
    elif key == pygame.K_g:
        gm.manual_grab()
    elif key == pygame.K_c:
        gm.manual_enter_door()


def create_window(title):
    """
    Opens the game window at full pixel density (sharp on Retina screens) when pygame-ce
    is installed; falls back to a regular window otherwise.
    Returns (surface to draw on, function that shows the frame).
    """
    if hasattr(pygame, "Window"):
        window = pygame.Window(title, WINDOW_SIZE, allow_high_dpi=True)
        return window.get_surface(), window.flip
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(title)
    return screen, pygame.display.flip


def main():
    # Pre-initialize mixer for low-latency audio
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()

    screen, show_frame = create_window("Agentic AI - Wumpus World")
    clock = pygame.time.Clock()

    sound_manager = SoundManager()
    world = World(num_rooms=3)
    agent = Agent(world)
    gm = GameManager(world, agent, sound_manager=sound_manager)
    renderer = Renderer(screen)
    dev_panel = DevPanel(gm, WINDOW_SIZE)
    controls = ControlPanel(renderer.bar_rect, gm, renderer, sound_manager, dev_panel)

    hand = pygame.SYSTEM_CURSOR_HAND
    arrow = pygame.SYSTEM_CURSOR_ARROW
    move = pygame.SYSTEM_CURSOR_SIZEALL
    last_auto_step = 0
    running = True

    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                handle_key(event.key, gm, renderer, dev_panel)
            elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                consumed = dev_panel.handle(event) or controls.handle(event)
                if not consumed and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    renderer.handle_click(event.pos)
                if event.type == pygame.MOUSEMOTION:
                    if dev_panel.dragging or dev_panel.hovering_header(event.pos):
                        cursor = move
                    elif dev_panel.hovering_control(event.pos):
                        cursor = hand
                    elif dev_panel.open and dev_panel.rect.collidepoint(event.pos):
                        cursor = arrow
                    elif controls.hovering(event.pos) or renderer.minimap_hover(event.pos):
                        cursor = hand
                    else:
                        cursor = arrow
                    pygame.mouse.set_cursor(cursor)

        if gm.auto_mode and not gm.game_over and now - last_auto_step >= gm.auto_delay_ms:
            gm.step_ai()
            last_auto_step = now

        dev_panel.update()
        renderer.draw(gm, controls)
        dev_panel.draw(renderer.p)
        show_frame()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
