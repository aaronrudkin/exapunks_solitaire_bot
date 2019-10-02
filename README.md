# exapunks_solitaire_bot

This code solves ПАСЬЯНС solitaire as implemented in Exapunks (not intended for public use at this time).

`exa_logic.py` contains all of the code to solve solitaire. `exa_gui.py` contains code to read the screen, detect the game being played, and implement the solution via mouse -- simply run `python exa_gui.py` to read directly from the screen or `python exa_gui.py screenshot.png` to load from a previously saved screenshot. To play multiple games in a row, start a new game, then run `python exa_gui.py loop n` where n is the number of games to play. Running `exa_logic.py` directly generates a random game and solves it.

Currently, the code expects the game to be running in a 1920x1080 window, unobscured, anywhere on the screen, and expects a 2x DPI screen (e.g. Mac Retina). To make it work with other resolutions or DPI scales, edit the pixel offsets found in `config.json`. The computer vision algorithm used to identify cards is OpenCV's template matching, and so when running in other resolutions you should also replace the card sprites found in `card_back/` with resolution appropriate ones.
