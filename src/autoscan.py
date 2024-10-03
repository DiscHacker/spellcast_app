import win32ui, win32gui, cv2, math, json, logging
import numpy as np
from ctypes import windll
from PIL import Image, ImageDraw, ImageFont
from src.searchnode import SearchNode
from src.spellcast import Spellcast
from functools import cmp_to_key
from scipy.ndimage import label
from paddleocr.ppocr.utils.logging import get_logger
from paddleocr import PaddleOCR

logger = get_logger()
logger.setLevel(logging.ERROR)

ocr = PaddleOCR(use_angle_cls=False, lang='en')

class AutoScan():
    def __init__(self):
        self.game = Spellcast()

    def draw_arrow(self, draw, start, end, color='red', width=3, arrow_size=15, shorten_factor=0.2):
        # Calculate the direction vector
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)

        # Shorten the arrow on both ends
        shorten = length * shorten_factor
        start_x = start[0] + (dx * shorten / length)
        start_y = start[1] + (dy * shorten / length)
        end_x = end[0] - (dx * shorten / length)
        end_y = end[1] - (dy * shorten / length)

        # Draw the line
        draw.line([(start_x, start_y), (end_x, end_y)], fill=color, width=width)
        
        # Calculate arrow head
        angle = math.atan2(end_y - start_y, end_x - start_x)
        x1 = end_x - arrow_size * math.cos(angle - math.pi/6)
        y1 = end_y - arrow_size * math.sin(angle - math.pi/6)
        x2 = end_x - arrow_size * math.cos(angle + math.pi/6)
        y2 = end_y - arrow_size * math.sin(angle + math.pi/6)
        
        draw.polygon([(end_x, end_y), (x1, y1), (x2, y2)], fill=color)

    def draw_swap(self, draw, char, position, square_size=30):
        char = char.upper()
        x, y = position
        half_size = square_size // 2
        left = x - half_size
        top = y - half_size

        draw.rectangle([left, top, left + square_size, top + square_size], fill="white")
        
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except IOError:
            font = ImageFont.load_default()
        
        left, top, right, bottom = draw.textbbox((0, 0), char, font=font)
        text_width = right - left
        text_height = bottom - top
        text_x = x - text_width // 2
        text_y = y - text_height // 2 - top

        draw.text((text_x, text_y), char, fill=(0, 204, 255), font=font)

    def coordinator(self, board: Image.Image, coordinates: list, swap_strings: dict):
        cell_width = board.width // 5
        cell_height = board.height // 5
        board_copy = board.copy()
        draw = ImageDraw.Draw(board_copy)

        for i in range(len(coordinates) - 1):
            start_x, start_y = coordinates[i]
            end_x, end_y = coordinates[i + 1]

            start_center_x = ((start_x-1) * cell_width) + (cell_width // 2)
            start_center_y = ((start_y-1) * cell_height) + (cell_height // 2)
            end_center_x = ((end_x-1) * cell_width) + (cell_width // 2)
            end_center_y = ((end_y-1) * cell_height) + (cell_height // 2)

            self.draw_arrow(draw, (start_center_x, start_center_y), (end_center_x, end_center_y))

            if swap_strings:
                if i==0:
                    if coordinates[i] in swap_strings: self.draw_swap(draw, swap_strings[coordinates[i]], (start_center_x, start_center_y))
                if coordinates[i+1] in swap_strings: self.draw_swap(draw, swap_strings[coordinates[i+1]], (end_center_x, end_center_y))
        
        return board_copy

    def seperator(self, image):
        image_array = np.array(image)
        black_mask = (image_array[:, :, 0] < 50) & (image_array[:, :, 1] < 50) & (image_array[:, :, 2] < 50)
        labeled_mask, _ = label(black_mask)
        sizes = np.bincount(labeled_mask.ravel())
        sizes[0] = 0 
        largest_component = np.argmax(sizes)
        final_mask = np.zeros_like(black_mask, dtype=bool)
        final_mask[labeled_mask == largest_component] = True
        output_image = np.ones_like(image_array) * 255
        output_image[final_mask] = image_array[final_mask]
        return Image.fromarray(output_image)

    def check_color(self, image, color, thres=20, exact=False, density_check=False, min_density=20):
        image_array = np.array(image)
        target_color = np.array(color)

        if exact:
            color_mask = np.all(image_array == target_color, axis=-1)
        else:
            diff = np.abs(image_array - target_color)
            color_mask = np.all(diff <= thres, axis=-1)

        if density_check:
            matching_pixels = np.sum(color_mask)
            return matching_pixels >= min_density

        return np.any(color_mask)

    def find_discord_window(self):
        name = str(input("INPUT GAME WINDOW: "))
        def enum_windows_callback(hwnd, windows):
            if name in win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows[0] if windows else None

    def get_image(self, hwnd):
        windll.user32.SetProcessDPIAware()
        left, top, right, bot = win32gui.GetClientRect(hwnd)
        w = right - left
        h = bot - top

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

        saveDC.SelectObject(saveBitMap)

        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return im

    def get_board(self, image):
        image = np.array(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        lower_color = np.array([130, 79, 0], dtype="uint8")
        upper_color = np.array([130, 79, 0], dtype="uint8")

        mask = cv2.inRange(image, lower_color, upper_color)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) == 0:
            raise ValueError("No contours found with the specified color!")

        largest_contour = None
        max_area = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                max_area = area
                largest_contour = contour

        if largest_contour is None:
            raise ValueError("No valid contour found!")

        x, y, w, h = cv2.boundingRect(largest_contour)
        cropped = image[y:y+h, x:x+w]
        cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        result_pil = Image.fromarray(cropped_rgb)
        image = result_pil.crop((14, 12, result_pil.width - 14, result_pil.height - 12))

        return image

    def get_cells(self, board):
        cell_width = board.width // 5
        cell_height = board.height // 5

        batch = []
        checks = []
        for i in range(5):
            for j in range(5):
                left = j * cell_width
                upper = i *  cell_height
                right = left + cell_width
                lower = upper + cell_height
                cell_image = board.crop((left, upper, right, lower))

                cropped_image = cell_image.crop((cell_width//4, cell_height//4, cell_width-(cell_width//4), cell_height-(cell_height//4)))
                batch.append(self.seperator(cropped_image))
                
                DL = self.check_color(cell_image, [255, 255, 170], density_check=True, min_density=50)
                TL = self.check_color(cell_image, [235, 122, 67], thres=40, density_check=True, min_density=50)
                GEM = self.check_color(cell_image, [255, 114, 255])
                X2 = self.check_color(cell_image, [255, 35, 235], exact=True, density_check=True, min_density=400)

                checks.append([X2, DL, TL, GEM])
        
        return batch, checks

    def get_chars(self, batch):
        chars = [ocr.ocr(np.array(img), det=False, rec=True)[0][0][0]
                for img in batch] 
        return chars

    def process_char(self, checks, char, index, plain=False):
        check = checks[index]
        char = char.replace('0', 'O').replace('1', 'I').strip(" ")
        char = char.upper()
        if plain: return char
        if check[0]: char+="$"
        if check[1]: char+="+"
        if check[2]: char+="*"
        if check[3]: char+="!"
        return char

    def run(self, checks, chars, swap=1):
        processed_chunks = []
        for i in range(0, len(chars), 5):
            chunk = "".join(self.process_char(checks, chars[j], j) for j in range(i, min(i + 5, len(chars))))
            processed_chunks.append(chunk)

        result_string = "\n".join(processed_chunks)
        print(result_string)

        if swap == 0: gem = '0'
        elif swap == 1: gem = '3'
        elif swap == 2: gem = '6'
        self.game.load_data(processed_chunks + [gem, '5'])

        config = json.load(open("config.json"))
        print("searching for moves...")

        def compare_moves(a: SearchNode, b: SearchNode):
            a_score = a.estimated_long_term_score(self.game)
            b_score = b.estimated_long_term_score(self.game)

            difference = a_score - b_score
            if difference == 0:
                return a.gem_count() - b.gem_count()
            else:
                return difference

        best_moves = self.game.legal_moves(
            cmp_to_key(compare_moves)
            if config["gemManagement"]
            else SearchNode.score
        )

        return best_moves[:config["movesShown"]]


# hwnd = find_discord_window()
# game = Spellcast()
# while True:
#     inp = input("OPTIONS: \n(NS/S/2S) Continue\n(1) Change window name\n(2) Exit\nINPUT: ")
#     match str(inp).lower():
#         case 'ns': swap = 0
#         case 's': swap = 1
#         case '2s': swap = 2
#         case '1':
#             hwnd = find_discord_window()
#             continue
#         case '2': exit()

#     start_time = time.time()

#     game_screen = get_image(hwnd)

#     try:
#         board_image = get_board(game_screen)
#     except ValueError:
#         hwnd = find_discord_window()
#         continue

    # batch, checks = get_cells(board_image)
    # chars = get_chars(batch)
    # results = run(checks, chars, swap)

    # for i, node in enumerate(results):
    #     word, score, gem, coordinates, swap_strings = node.to_string(game)
    #     print(f"{i + 1} > {word} - {score} points - {gem} gems")
    #     if swap_strings: print(f"   Swaps: {swap_strings}")
    #     print(f"   Coordinates: {' -> '.join(map(str, coordinates))}")
    #     print()

#         coordinator(board_image, coordinates, swap_strings)

#     print(round(time.time() - start_time, 2))