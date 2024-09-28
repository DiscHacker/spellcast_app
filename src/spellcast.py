from collections import deque
from src.board import Board
from src.tile import TileModifier
from src.searchnode import SearchNode
from src.gems import AVERAGE_SCORES, AVERAGE_NET_GEM_PROFITS, gem_value
import src.dictionary as dictionary
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor, as_completed

@lru_cache(maxsize=None)
def cached_has_word(word):
    return dictionary.has_word(word)

@lru_cache(maxsize=None)
def cached_has_prefix(prefix):
    return dictionary.has_prefix(prefix)

class Spellcast(Board):
    def legal_moves_from(self, x: int, y: int):
        legal_move_nodes: list[SearchNode] = []
        stack: deque[tuple[SearchNode, str, set]] = deque()
        
        root_tile = self.tile_at(x, y)
        root_node = SearchNode(None, root_tile)
        
        stack.append((root_node, root_tile.letter, {(x, y)}))
        
        max_depth = 15  # Set a reasonable maximum depth
        
        while stack:
            current_node, word, visited = stack.pop()
            
            if len(word) > max_depth:
                continue
            
            if dictionary.has_word(word):
                legal_move_nodes.append(current_node)
            
            adjacent_tiles = self.adjacent_tiles(current_node.x, current_node.y)
            
            for adjacent_tile in adjacent_tiles:
                if TileModifier.FROZEN in adjacent_tile.modifiers:
                    continue
                
                new_pos = (adjacent_tile.x, adjacent_tile.y)
                if new_pos in visited:
                    continue
                
                new_node = SearchNode(current_node, adjacent_tile)
                new_word = word + adjacent_tile.letter
                new_visited = visited.copy()
                new_visited.add(new_pos)
                
                if dictionary.has_prefix(new_word):
                    stack.append((new_node, new_word, new_visited))
                
                # Handle swaps
                if self.gems >= 3 * (current_node.swap_count() + 1):
                    for swap_letter in dictionary.alphabet:
                        if swap_letter == adjacent_tile.letter:
                            continue
                        
                        swap_word = word + swap_letter
                        if dictionary.has_prefix(swap_word):
                            swap_node = SearchNode(current_node, adjacent_tile, True)
                            swap_node.letter = swap_letter
                            stack.append((swap_node, swap_word, new_visited))
        
        return legal_move_nodes
    

    def legal_moves(self, sort_key = None, sort_reverse: bool = True):
        with ProcessPoolExecutor() as executor:
            futures = []
            for y in range(len(self.tiles)):
                for x in range(len(self.tiles[y])):
                    if TileModifier.FROZEN not in self.tile_at(x, y).modifiers:
                        futures.append(executor.submit(self.legal_moves_from, x, y))

            all_moves = []
            for future in as_completed(futures):
                all_moves.extend(future.result())

        unique_move_map = {}
        for move in all_moves:
            word = move.word()
            existing_move = unique_move_map.get(word)
            if existing_move is None or move.score() > existing_move.score() or \
            (move.score() == existing_move.score() and move.swap_count() < existing_move.swap_count()) or \
            (move.score() == existing_move.score() and move.swap_count() == existing_move.swap_count() and move.gem_count() > existing_move.gem_count()):
                unique_move_map[word] = move

        legal_move_nodes = list(unique_move_map.values())

        if sort_key is not None:
            legal_move_nodes.sort(key=sort_key, reverse=sort_reverse)

        return legal_move_nodes
    

    def evaluate_shuffle(self, top_move: SearchNode) -> tuple[int, bool]:
        if self.gems == 0:
            return (0, False)

        simulated_score = 0
        simulated_gems = self.gems - 1
        next_round_gem_count = 0

        # simulate a shuffle and the next round
        for round_index in range(min(2, 6 - self.match_round)):
            simulated_score += AVERAGE_SCORES[int(simulated_gems / 3)]
            simulated_gems += AVERAGE_NET_GEM_PROFITS[int(simulated_gems / 3)]
            
            if round_index == 0:
                next_round_gem_count = simulated_gems

        # add value of leftover gems
        if self.match_round < 4:
            simulated_score += gem_value(next_round_gem_count)

        # add value of remaining gems for last round
        if self.match_round == 5:
            simulated_score += simulated_gems

        # get value of the spent shuffle gem
        shuffle_gem_value = gem_value(self.gems) - gem_value(self.gems - 1)

        # return the estimated long term score and
        # whether a shuffling recommendation should be made
        return (
            simulated_score,
            simulated_score > (
                top_move.estimated_long_term_score(self)
                + shuffle_gem_value
            )
        )