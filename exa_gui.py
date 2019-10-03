"""
Handles the screen capture, asking exa_logic to solve the game, using the mouse
to solve the game.
"""

from __future__ import print_function
import glob
import json
import sys
import time
import cv2
import mss
import numpy as np
import pyautogui
import six
from PIL import Image
import exa_logic

CONFIG = json.load(open("config.json"))


def anchor_and_clip(image):
    """
    Locates the Exapunks game inside the full screenshot and clips it out.
    """

    corner = cv2.imread(CONFIG["anchor_filename"])
    result = cv2.matchTemplate(image, corner, cv2.TM_SQDIFF)
    x, y = cv2.minMaxLoc(result)[2]

    crop_image = image[
        y:y + CONFIG["max_window_y"],
        x:x + CONFIG["max_window_x"]
    ]
    return x, y, crop_image


def read_freecells():
    """
    Determines how many unlocked free cells there are. For exapunks, this is
    always one unlocked cell.
    """
    return [0]


def read_stacks(image):
    """ Determines which cards are in which stack """

    cards = []
    card_names = []
    for file_iterator in glob.glob(CONFIG["card_filename"]):
        card_name = file_iterator.rsplit("/", 1)[1].split(".")[0]
        card_names.append(card_name)
        cards.append(cv2.imread(file_iterator))

    stacks = []
    for x_stack in range(CONFIG["number_stacks"]):
        stack = []
        for y_stack in range(CONFIG["cards_per_stack_base"]):
            coord_x = (
                CONFIG["base_stack_offset_x"] +
                (CONFIG["stack_width"] * x_stack)
            )
            coord_y = (
                CONFIG["base_stack_offset_y"] +
                (CONFIG["stack_height"] * y_stack)
            )
            crop_image = image[
                coord_y:coord_y + CONFIG["card_sprite_y"],
                coord_x:coord_x + CONFIG["card_sprite_x"]
            ]

            result_scores = [
                cv2.matchTemplate(crop_image, cards[i], cv2.TM_SQDIFF)
                for i in range(len(cards))
            ]

            card_type = card_names[result_scores.index(min(result_scores))]
            stack.append(card_type)

        stacks.append(stack)

    return stacks


def computer_hash(my_image):
    """
    Uses image to build the game, returns information for solving the game
    """

    print("Beginning screen detection")
    offset_screen_x, offset_screen_y, my_image = anchor_and_clip(my_image)
    freecells = read_freecells()
    freecell_hash = "".join(["F/" if x == 0 else "FL/" for x in freecells])
    stacks = read_stacks(my_image)
    stack_hash = "".join(
        ["S%s/" % "".join([str(s) for s in stack]) for stack in stacks]
    )
    print("Done. Game detected.")
    return [offset_screen_x, offset_screen_y, stack_hash + freecell_hash]


def read_file(filename):
    """ Reads a screenshot from a file and solves it. """
    print("Beginning file read...")
    my_image = cv2.imread(filename)
    return computer_hash(my_image)


def grab_screenshot():
    """ Takes a screenshot from the screen and solves it. """
    print("Taking screenshot...")
    with mss.mss() as screenshot:
        monitor = screenshot.monitors[0]
        shot = screenshot.grab(monitor)
        frame = np.array(
            Image.frombytes("RGB", (shot.width, shot.height), shot.rgb)
        )
        frame_2 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return computer_hash(frame_2)


def execute_solution(offset_x, offset_y, moves):
    """ Executes solution by moving mouse and clicking. """

    # First, click the window
    pyautogui.mouseDown(
        (offset_x + CONFIG["window_click_offset_x"]) *
        CONFIG["resolution_scale_click"],
        (offset_y + CONFIG["window_click_offset_y"]) *
        CONFIG["resolution_scale_click"],
        button="left"
    )
    time.sleep(CONFIG["base_delay"] * 3)
    pyautogui.mouseUp()
    time.sleep(CONFIG["base_delay"] * 5)

    # Now, replay the moves one by one
    for move in moves:
        # which stack, how many cards down -> which stack, how many cards down
        x_pre, y_pre, x_post, y_post = move

        # If it's a regular stack, move to the offset
        if x_pre < CONFIG["number_stacks"]:
            x_pre_final = (
                offset_x +
                CONFIG["base_stack_offset_x"] +
                (CONFIG["stack_width"] * x_pre) +
                CONFIG["click_offset_x"]
            )
            y_pre_final = (
                offset_y +
                CONFIG["base_stack_offset_y"] +
                (CONFIG["stack_height"] * y_pre) +
                CONFIG["click_offset_y"]
            )
        # Separate offsets for freecell
        else:
            x_pre_final = (
                offset_x +
                CONFIG["freecell_offset_x"] +
                (CONFIG["stack_width"] * (x_pre - CONFIG["number_stacks"])) +
                CONFIG["click_offset_x"]
            )
            y_pre_final = (
                offset_y +
                CONFIG["freecell_offset_y"] +
                CONFIG["click_offset_y"]
            )

        if x_post < CONFIG["number_stacks"]:
            x_post_final = (
                offset_x +
                CONFIG["base_stack_offset_x"] +
                (CONFIG["stack_width"] * x_post) +
                CONFIG["click_offset_x"]
            )
            y_post_final = (
                offset_y +
                CONFIG["base_stack_offset_y"] +
                (CONFIG["stack_height"] * y_post) +
                CONFIG["click_offset_y"]
            )
        else:
            x_post_final = (
                offset_x +
                CONFIG["freecell_offset_x"] +
                (CONFIG["stack_width"] * (x_post - CONFIG["number_stacks"])) +
                CONFIG["click_offset_x"]
            )
            y_post_final = (
                offset_y +
                CONFIG["freecell_offset_y"] +
                CONFIG["click_offset_y"]
            )

        # Move the mouse to the beginning place
        pyautogui.moveTo(
            x_pre_final * CONFIG["resolution_scale_click"],
            y_pre_final * CONFIG["resolution_scale_click"],
            duration=CONFIG["base_delay"]
        )

        # Click and drag to the end
        pyautogui.dragTo(
            x_post_final * CONFIG["resolution_scale_click"],
            y_post_final * CONFIG["resolution_scale_click"],
            duration=CONFIG["base_delay"],
            button="left"
        )

        # Wait for a while
        time.sleep(CONFIG["base_delay"])


def click_new_game(offset_x, offset_y):
    """ Literally just clicks the new game button. """

    pyautogui.mouseDown(
        (offset_x + CONFIG["new_game_offset_x"]) *
        CONFIG["resolution_scale_click"],
        (offset_y + CONFIG["new_game_offset_y"]) *
        CONFIG["resolution_scale_click"],
        button="left"
    )
    time.sleep(CONFIG["base_delay"] * 3)
    pyautogui.mouseUp()
    time.sleep(CONFIG["base_delay"] * 5)


def loop_many(max_i=3):
    """
    Plays more than one game in a row, clicking new game when necessary.
    """

    # Just play a bunch of games
    for i in range(max_i):
        offset_x, offset_y, game_hash = grab_screenshot()
        game = exa_logic.Game()
        game.exact_setup(game_hash)
        result = game.global_solve(-1)
        execute_solution(offset_x, offset_y, result)

        print("Done game %d / %d... " % (i + 1, max_i))
        time.sleep(4)

        if i < max_i - 1:
            click_new_game(offset_x, offset_y)
            time.sleep(CONFIG["base_delay"] * 25)


def main():
    """
    Dispatches by reading file argument on command line or taking snapshot
    of screen.
    """

    if len(sys.argv) > 1 and sys.argv[1]:
        if sys.argv[1] == "loop":
            loop_many(int(sys.argv[2]))
            return

        _, _, game_hash = read_file(sys.argv[1])
        offset_x = 0
        offset_y = 0
    else:
        offset_x, offset_y, game_hash = grab_screenshot()

    print(hash)
    game = exa_logic.Game()
    game.exact_setup(game_hash)
    print(game)
    result = game.global_solve(-1)
    print(result)

    # If it was a screen grab, we can actually do this -- just type n/q/c to
    # quit or anything else to continue
    if result is not None and offset_x and offset_y:
        x = six.moves.input("Ready for automated solution? ")
        if x.lower() in ["n", "q", "c"]:
            return

        execute_solution(offset_x, offset_y, result)


if __name__ == "__main__":
    main()
