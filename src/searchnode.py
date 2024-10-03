from typing_extensions import Self
from json import load
from src.tile import Tile, TileModifier
from src.gems import AVERAGE_SCORES, gem_value

config = load(open("config.json"))


class SearchNode(Tile):
    parent: Self | None

    letter: str
    swap: bool
    

    def __init__(self, parent: Self, tile: Tile, swap: bool = False):
        super().__init__(tile.letter, tile.x, tile.y)
        self.modifiers = tile.modifiers

        self.parent = parent
        self.swap = swap

        self._word = None
        self._score = None
        self._gem_count = None
        self._swap_count = None


    def to_string(self, context = None):
        swap_strings = {}
        for chain_node in self.chain():
            if not chain_node.swap:
                continue
            swap_strings[(chain_node.x + 1, chain_node.y + 1)] = chain_node.letter.upper()

        coordinates = [(chain_node.x + 1, chain_node.y + 1) for chain_node in self.chain()]

        return self.word(), self.score(context), self.gem_count(), coordinates, swap_strings


    def chain(self):
        nodes: list[Self] = [self]

        while nodes[0].parent is not None:
            nodes.insert(0, nodes[0].parent)

        return nodes
    

    def chain_contains(self, x: int, y: int):
        for chain_node in self.chain():
            if chain_node.x == x and chain_node.y == y:
                return True
            
        return False
    

    def word(self):
        if self._word is None:
            self._word = "".join([chain_node.letter for chain_node in self.chain()])
        return self._word
    

    def score(self, context=None):
        if self._score is None:
            score = 0
            double_word_score = False
            gem_count = 0
            word_length = 0

            chain = self.chain()
            for chain_node in chain:
                score += chain_node.value()
                word_length += 1

                if TileModifier.DOUBLE_WORD in chain_node.modifiers:
                    double_word_score = True

                if TileModifier.GEM in chain_node.modifiers:
                    gem_count += 1

            if double_word_score:
                score *= 2

            if word_length >= 6:
                score += 10

            if context is not None and context.match_round == 5:
                score += gem_count

            self._score = score
            self._gem_count = gem_count  # Cache gem_count for future use

        return self._score


    def estimated_long_term_score(self, context):
        long_term_score = self.score(context)

        final_gem_count = min(10, context.gems + self.net_gem_profit())

        if context.match_round < 5:  
            long_term_score += AVERAGE_SCORES[final_gem_count // 3]

        if context.match_round < 4:
            long_term_score += gem_value(final_gem_count)

        return long_term_score


    def net_gem_profit(self):
        return self.gem_count() - (self.swap_count() * 3)


    def gem_count(self):
        if self._gem_count is None:
            self._gem_count = sum(TileModifier.GEM in chain_node.modifiers for chain_node in self.chain())
        return self._gem_count


    def swap_count(self):
        if self._swap_count is None:
            self._swap_count = sum(chain_node.swap for chain_node in self.chain())
        return self._swap_count
