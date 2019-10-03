"""
Implements the entire game logic portion of this Solitaire solver -- enough to
produce a valid game and solid it, or take a specific game and solve it.
"""

from __future__ import print_function
from collections import deque
from timeit import default_timer as timer
import random
import copy
import time


class Stack(object):
    """
    A stack is a place where cards can go; types are 'stack' and 'freecell'.
    """

    face_values = ["H", "S", "C", "D"]
    num_values = ["6", "7", "8", "9"]
    face_cards = ["HH", "SS", "CC", "DD"]

    def __init__(self, card_type, locked):
        self.card_type = card_type
        self.locked = locked
        self.stack = []
        self.past_cards = ""

    def __str__(self):
        """ Quick way to print out the contents of this stack to the user. """
        return "Type: %s%s: %s" % (self.card_type,
                                   " [Locked]" if self.locked else "",
                                   str(self.stack))

    def hash(self):
        """
        This function is a hash of what's going on in the stack, used to
        verify we haven't visited this location before.
        """

        type_str = self.card_type[0].upper()
        if self.stack != "X":
            card_str = "".join([str(x) for x in self.stack])
        else:
            card_str = "X[" + str(self.past_cards) + "]"
        return type_str + card_str

    def init_cards(self, cards):
        """ Adds the initial cards to the stack. """
        if self.stack:
            raise Exception("Illegal init, cards already there")

        if self.card_type == "freecell":
            raise Exception("Illegal init, can't init cards in free cell")

        self.stack = cards

    @classmethod
    def compatible(cls, top, bottom):
        """
        Tests compatibility of two cards -- can bottom be placed under top in
        a solitaire context?
        """
        top_str, top_suit = list(top)
        bottom_str, bottom_suit = list(bottom)

        if top_suit == bottom_suit and top_str in cls.face_values:
            return 1

        if (top_str in cls.face_values or bottom_str in cls.face_values):
            return 0

        top_number = int(top_str) if top_str in cls.num_values else 10
        bottom_number = int(bottom_str) if bottom_str in cls.num_values else 10

        if bottom_number == top_number - 1 and top_suit != bottom_suit:
            return 1

        return 0

    def is_move_to_legal(self, card):
        """ Is a move described by the argument 'card' to this stack legal? """

        # If stack is locked, not valid
        if self.locked:
            return 0

        # If it's a freecell and it already has something, not valid
        if self.card_type == "freecell" and self.stack:
            return 0

        # If it's a freecell and you're trying to move more than one card, not
        # valid
        if self.card_type == "freecell" and len(card) > 1:
            return 0

        # If it's a stack and there are cards and the card you're moving
        # doesn't match the last card on the stack, not valid
        if (self.card_type == "stack" and self.stack and not
                self.compatible(self.stack[-1], card[0])):
            return 0

        return 1

    def is_move_from_legal(self):
        """ Is there a legal move from this stack? """

        # If it's locked, no
        if self.locked:
            return 0

        # If there's nothing here, no
        if not self.stack:
            return 0

        return 1

    def resolve_move_to(self, card):
        """ Actually modify the stack by moving the card. """

        # If we can't do this move then error
        if not self.is_move_to_legal(card):
            raise Exception("Trying to force illegal move")

        # Do the move
        self.stack = self.stack + card

        # If we just created a collapse, handle the collapse
        if (len(self.stack) == 4 and self.stack == [self.stack[0]] * 4 and
                self.stack[0] in self.__class__.face_cards):
            # Lock the stack, save which card type was in the lock for user
            # debug, mark the stack cards as X
            self.locked = True
            self.past_cards = self.stack[0]
            self.stack = "X"

    def which_cards_moving(self):
        """
        We're moving from this stack -- how many cards do we take? So if the
        stack ends with 2 of the same card, both move.
        """

        # By default, it's one card
        card_move = [self.stack[-1]]

        # How many more?
        for i in range(len(self.stack) - 2, -1, -1):
            if not self.compatible(self.stack[i], card_move[-1]):
                break

            card_move.append(self.stack[i])

        # We appended the cards backwards, so let's reverse to correct.
        card_move.reverse()

        # Return the cards
        return card_move

    def resolve_move_from(self, max_stack=0):
        """
        Actually modify the stack by removing the cards. 'max_stack' argument
        limits the number of cards we can move.
        """

        # Again, make sure we can actually do this move
        if not self.is_move_from_legal():
            raise Exception("Trying to force illegal move")

        # If there's no max stack, just take all the cards we can. If not, only
        # take the maximum number.
        if not max_stack:
            card_move = self.which_cards_moving()
        else:
            card_move = self.stack[-max_stack:]

        # Figure out what's left
        remaining_keep = len(self.stack) - len(card_move)
        if len(card_move) == len(self.stack):
            self.stack = []
        else:
            self.stack = self.stack[0:remaining_keep]

        # Return the cards that are leaving
        return card_move

    def is_complete(self):
        """
        Quick check: Is this stack collapsed and done? Used for detecting game
        end.
        """
        if self.stack == "X":
            return 1

        # The two different patterns of complete number cards
        if (self.stack == ["0R", "9B", "8R", "7B", "6R"] or
                self.stack == ["0B", "9R", "8B", "7R", "6B"]):
            return 1

        return 0


class Game(object):
    """
    A game is a collection of stacks and rules governing the generation
    of plausible moves, as well as a meta-solver function that solves the game.
    """

    face_cards = ["HH", "SS", "CC", "DD"] * 4
    number_cards = [
        "0B", "0R", "9B", "9R", "8B",
        "8R", "7B", "7R", "6B", "6R"
    ] * 2

    def __init__(self, card_stacks=9, freecells=1, max_depth=100):
        """
        Initial setup of the stacks and free cells; 'how_many_free' is the
        number of unlocked freecells.
        """

        base_stacks = [Stack("stack", 0) for _ in range(card_stacks)]
        cell_stacks = [Stack("freecell", 0) for _ in range(freecells)]
        self.stacks = base_stacks + cell_stacks
        self.card_stacks = card_stacks
        self.depth = 0
        self.max_depth = max_depth
        self.move_history = []
        self.score = 0

    def __str__(self):
        """ Again, user-friendly printing helper. """
        base_str = "Current Game State...\n=======\n"
        for i in range(len(self.stacks)):
            base_str += "#%d %s\n" % (i, str(self.stacks[i]))

        base_str += self.hash() + "\n"
        base_str += "====="

        return base_str

    def hash(self):
        """ Hash the entire game, one stack at a time. """
        stack_chunks = []
        for i in range(len(self.stacks)):
            stack_chunks.append("%s/" % self.stacks[i].hash())

        # Why do we sort the stacks? Imagine a game with just two stacks, one
        # which has 888, and one which is empty. "888 / empty" is the same
        # game as "empty / 888". Sorting resolves this
        stack_chunks.sort()
        stack_text = "".join(stack_chunks)

        return stack_text

    @staticmethod
    def seed(seed):
        """
        Very dumb helper to set seed. I thought I might need something more
        sophisticated, but I didn't.
        """
        random.seed(seed)

    def deal_cards(self):
        """ If we don't have a game in mind, generate a random one. """

        # 6-10 black and red * 2, 4x each face color
        cards = self.__class__.face_cards + self.__class__.number_cards

        # Shuffle
        random.shuffle(cards)

        # Divide into stacks
        new_stacks = [cards[(i * 4):(i * 4) + 4] for i in
                      range(self.card_stacks)]

        # Initialize the actual stacks
        for i in range(self.card_stacks):
            self.stacks[i].init_cards(new_stacks[i])

    def exact_setup(self, game_hash):
        """ Play a specific game based on a user-provided hash. """

        stack_set = []

        stack_hashes = [x for x in game_hash.split("/") if len(x)]
        for stack in stack_hashes:
            stack_type = "stack" if stack[0] == "S" else "freecell"

            past_card = -1

            if len(stack) == 1:
                cards = []
                lock_type = 0
            elif not stack[1:].startswith("X"):
                cards = list([stack[(1 + i):(1 + i + 2)] for i in
                              range(0, len(stack[1:]), 2)])
                lock_type = 0
            else:
                lock_type = 1
                cards = "X"
                past_card = int(stack[3:5])

            new_stack = Stack(stack_type, lock_type)
            new_stack.stack = cards
            if past_card > -1:
                new_stack.past_cards = past_card

            stack_set.append(new_stack)

        # Overwrite the game's whole stack set with the stacks.
        self.stacks = stack_set

    def get_score(self, override=0):
        """ Score for current game. These point values were my first guess. """

        # We've already calculated a score, so just return it
        if self.score and not override:
            return self.score

        score = 0
        # Iterate over the stacks
        for i in self.stacks:
            # Collapsed? 20 points
            if i.is_complete():
                score = score + 20
            # Empty stack? 10 points
            elif i.card_type == "stack" and not i.stack:
                score = score + 10
            # Stack with cards? 5 - the number of inaccessible cards.
            elif i.card_type == "stack" and i.stack:
                # What does a complete stack look like?
                if (len(i.stack) == 5 and
                    (i.stack == ["0R", "9B", "8R", "7B", "6R"] or
                     i.stack == ["0B", "9R", "8B", "7R", "6B"])):
                    score = 10
                else:
                    num_cards_trapped = next(
                        (j + 1 for j in range(len(i.stack) - 2, -1, -1) if not
                         i.compatible(i.stack[j], i.stack[j + 1])), 0)
                    score = score + 5 - num_cards_trapped

        self.score = score
        return score

    def is_complete(self):
        """
        Is the game complete? Check all stacks and look for collapsed stacks
        equal in number to card types.
        """

        num_complete = sum([self.stacks[i].is_complete() for i in
                            range(len(self.stacks))])
        return num_complete == 8

    def is_dead(self):
        """ If there are no valid moves, this method of proceeding is dead. """
        return len(self.enumerate_moves()) == 0

    def enumerate_moves(self):
        """ List all valid moves but don't execute them. """

        valid_moves = []

        # Check moves from every cell to every cell using a nested loop. The i
        # iterator will be the destination and the j iterator the origin.
        for i in range(len(self.stacks)):
            # Don't bother checking moves to locked cell
            if self.stacks[i].locked:
                continue

            # And now the origin
            for j in range(len(self.stacks)):
                # Self move isn't a valid move
                if j == i:
                    continue

                # Don't just undo the previous move (the state iterator in
                # global_solve should prevent this anyway)
                if self.move_history and self.move_history[-1] == (i, j):
                    continue

                # Valid moves -- it's valid only if the top card in the
                # current movable stack would be a legal move
                if (self.stacks[j].is_move_from_legal() and
                    self.stacks[i].is_move_to_legal(
                        [self.stacks[j].which_cards_moving()[0]])):
                    valid_moves.append((j, i))

        # Return all valid moves
        return valid_moves

    def play_game(self, moves, print_level):
        """
        Once a solution has been found, execute the move set and print the
        output.
        """

        # No moves??? Uh????
        if not moves:
            raise Exception("No moves for successful game solve?")

        count = 1
        fixed_moves = []

        # Iterate the moves and unpack
        for i, j in moves:

            # Take the cards off the origin stack
            if self.stacks[j].card_type == "freecell":
                cards_move = self.stacks[i].resolve_move_from(1)
            else:
                cards_move = self.stacks[i].resolve_move_from(0)

            y_offset_pre = len(self.stacks[i].stack) - len(cards_move)
            y_offset_post = max(0, len(self.stacks[j].stack) - 1)

            # The text we're going to print
            unlock_text = ""
            cards_move_text = "[%s]" % ", ".join([str(c) for c in cards_move])
            old_stack_text = "[%s]" % ", ".join([str(c) for c in
                                                 self.stacks[j].stack])

            # Now put the card on the destination stack.
            self.stacks[j].resolve_move_to(cards_move)

            # Check if that collapsed
            if self.stacks[j].stack != "X":
                new_stack_text = "[%s]" % ", ".join([str(c) for c in
                                                     self.stacks[j].stack])
            else:
                new_stack_text = "Collapse"

            # Show the user
            if print_level > -1:
                print("Move %d: Move from %s %d to %s %d" %
                      (count, self.stacks[i].card_type, i,
                       self.stacks[j].card_type, j))
                print("  %s -> %s = %s%s" %
                      (cards_move_text, old_stack_text,
                       new_stack_text, unlock_text))

            fixed_moves.append((i, y_offset_pre, j, y_offset_post))
            count += 1

        # Hand back the same move set with numbers of cards attached for
        # whatever reason
        return fixed_moves

    def global_solve(self, print_level=0):
        """ Greedy hill-climber queue search to solve the game. """

        # Because this isn't recursive, only the top level should call this
        if self.depth > 0:
            raise Exception("Should only call this from top level.")

        begin = timer()
        print("Solving game...")

        # Record previously visited game states to avoid loops
        visited_nodes = []

        # deque is an efficient fifo data structure, but this might not
        # actually matter given we're re-sorting the queue later.
        nodes_to_visit = deque([self])

        # These are mostly about print outputs --
        max_depth = 0
        max_score = 0
        i = 0
        done = 0

        # Let's just go through the queue
        while nodes_to_visit:
            current = nodes_to_visit.popleft()

            # Have we already been to the state we're trying to go to?
            game_hash = current.hash()
            if game_hash in visited_nodes:
                continue

            # Print anything?
            if print_level > 0 and (current.get_score() > max_score or
                                    current.depth > max_depth or
                                    print_level == 2):
                print("%d [D%d L%d]: %s. Score: %d" %
                      (i, current.depth, len(nodes_to_visit),
                       current.hash(), current.get_score()))
                max_depth = max(max_depth, current.depth)
                max_score = max(max_score, current.get_score())

            # Mark this new state as having been visited
            visited_nodes.append(current.hash())

            # Are we done here?
            if current.is_complete():
                end = timer()
                print("Game complete in %d moves. Time elapsed %.2f seconds" %
                      (len(current.move_history), round(end - begin, 2)))
                result_moves = self.play_game(
                    current.move_history, print_level)
                done = 1
                break

            # If not, let's play -- what are my current descendents?
            results = current.solve()
            if results is not None:
                # Add the current descendents to the queue
                nodes_to_visit.extend(results)

                # Cheat by sorting -- greedy hill climb
                nodes_to_visit = deque(sorted(nodes_to_visit,
                                              key=lambda k: -k.get_score()))
            i += 1

        # Note to the user it's not solvable
        if not done:
            print("Game cannot be solved.")
            return []

        return result_moves

    def solve(self):
        """ Ask the current game state for its immediate children. """

        # Soft cap on complexity. This typically doesn't get invoked.
        if self.depth > self.max_depth:
            return None

        # If it's complete the global solver should have noticed
        if self.is_complete():
            raise Exception("Trying to solve complete game.")

        # No moves? Die.
        if self.is_dead() and self.depth > 0:
            return None

        # Get ready to store the children
        results = []
        valid_moves = self.enumerate_moves()

        # Iterate through moves
        for move in valid_moves:
            i, j = move

            # Child is a copy of the current game which we'll modify
            new_game = copy.deepcopy(self)

            # When resolving, there are two routes -- move one of stack
            # to freecell, or move all of stack somewhere.
            if new_game.stacks[j].card_type == "freecell":
                cards_move = new_game.stacks[i].resolve_move_from(1)
            else:
                cards_move = new_game.stacks[i].resolve_move_from(0)

            # Run the move
            new_game.stacks[j].resolve_move_to(cards_move)

            # Now add 1 to child depth, add the move to the move history,
            # pre-bake the score, and add to the list of children
            new_game.depth = new_game.depth + 1
            new_game.move_history.append(move)
            new_game.get_score(1)
            results.append(new_game)

        # This was a secondary check in case I wanted to limit valid moves in
        # the above iterator, but I ultimately didn't, so this should never
        # happen
        if self.depth == 0 and not results:
            raise Exception("Impossible to solve game")

        # No results?
        if not results:
            return None

        # Results
        return results


def main():
    """
    Dumb helper to run basic launch from terminal functionality of exa_logic.py
    """
    my_game = Game()
    my_game.deal_cards()

    print(my_game)
    time.sleep(0.5)
    my_game.global_solve(0)


if __name__ == "__main__":
    main()
