from src.board import Board
from src.tile import TileModifier, Tile
from src.searchnode import SearchNode
from src.gems import AVERAGE_SCORES, AVERAGE_NET_GEM_PROFITS, gem_value
import src.dictionary as dictionary
from functools import lru_cache
from multiprocessing import Pool
import os

@lru_cache(maxsize=None)
def cached_has_word(word):
    return dictionary.has_word(word)

@lru_cache(maxsize=None)
def cached_has_prefix(prefix):
    return dictionary.has_prefix(prefix)

class Spellcast(Board):
    def legal_moves_from(self, x: int, y: int):
        legal_move_nodes = []
        stack = [(SearchNode(None, self.tile_at(x, y)), self.tile_at(x, y).letter, {(x, y)})]
        
        max_depth = 15
        min_word_length = 5
        min_score_threshold = 15
        
        while stack:
            current_node, word, visited = stack.pop()
            
            if len(word) > max_depth:
                continue
            
            # Early pruning based on word length and score
            if len(word) >= min_word_length:
                if cached_has_word(word):
                    score = self.quick_score_estimate(current_node)
                    if score >= min_score_threshold:
                        legal_move_nodes.append(current_node)
            
            for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                new_x, new_y = current_node.x + dx, current_node.y + dy
                if 0 <= new_x < 5 and 0 <= new_y < 5:
                    adjacent_tile = self.tile_at(new_x, new_y)
                    if TileModifier.FROZEN in adjacent_tile.modifiers:
                        continue
                    
                    new_pos = (new_x, new_y)
                    if new_pos in visited:
                        continue
                    
                    new_node = SearchNode(current_node, adjacent_tile)
                    new_word = word + adjacent_tile.letter
                    new_visited = visited | {new_pos}
                    
                    if cached_has_prefix(new_word):
                        stack.append((new_node, new_word, new_visited))
                    
                    # Handle swaps
                    if self.gems >= 3 * (current_node.swap_count() + 1):
                        for swap_letter in dictionary.alphabet:
                            if swap_letter == adjacent_tile.letter:
                                continue
                            
                            swap_word = word + swap_letter
                            if cached_has_prefix(swap_word):
                                swap_node = SearchNode(current_node, adjacent_tile, True)
                                swap_node.letter = swap_letter
                                stack.append((swap_node, swap_word, new_visited))
        
        return legal_move_nodes
    
    def quick_score_estimate(self, node):
        score = 0
        word = node.word()
        for letter in word:
            score += Tile(letter, 0, 0).value()
        if len(word) >= 6:
            score += 10
        return score
    
    def legal_moves_from_parallel(self, start_positions):
        with Pool(processes=os.cpu_count()) as pool:
            results = pool.starmap(self.legal_moves_from, start_positions)
        return [move for sublist in results for move in sublist]

    def legal_moves(self, sort_key=None, sort_reverse: bool = True):
        start_positions = [
            (x, y) for y in range(len(self.tiles))
            for x in range(len(self.tiles[y]))
            if TileModifier.FROZEN not in self.tile_at(x, y).modifiers
        ]
        all_moves = self.legal_moves_from_parallel(start_positions)

        pruned_moves = self.prune_moves(all_moves)
        if sort_key is not None:
            pruned_moves.sort(key=sort_key, reverse=sort_reverse)
        return pruned_moves
    
    
    def prune_moves(self, moves):
        word_score_map = {}
        for move in moves:
            word = move.word()
            score = move.score(self)
            if word not in word_score_map or score > word_score_map[word][0]:
                word_score_map[word] = (score, move)

        return [move for _, move in word_score_map.values()]
    

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