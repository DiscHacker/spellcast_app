if __name__ == "__main__":
    
    from time import time
    from json import load
    from functools import cmp_to_key
    from src.spellcast import Spellcast
    from src.searchnode import SearchNode
    game = Spellcast()

    def main():
        config = load(open("config.json"))

        with open("board.txt", 'r') as file:
            lines = file.readlines()
            game.load_data(lines)

        start_time = time()
        print("searching for moves...")

        def compare_moves(a: SearchNode, b: SearchNode):
            a_score = a.estimated_long_term_score(game)
            b_score = b.estimated_long_term_score(game)

            difference = a_score - b_score
            if difference == 0:
                return a.gem_count() - b.gem_count()
            else:
                return difference


        best_moves = game.legal_moves(
            cmp_to_key(compare_moves)
            if config["gemManagement"]
            else SearchNode.score
        )

        for i, node in enumerate(best_moves[:config["movesShown"]]):
            word, score, gem, coordinates, swap_strings = node.to_string(game)
            print(f"{i + 1} > {word} - {score} points - {gem} gems")
            if swap_strings: print(f"   Swaps: {swap_strings}")
            print(f"   Coordinates: {' -> '.join(map(str, coordinates))}")
            print()

    main()