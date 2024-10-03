## A forked version of [WintrCat's spellcastsolver](https://github.com/wintrcat/spellcastsolver) with the following improvement
- Improved solving speed, by using multiprocessing and optimized alogorithm, overall time taken reduced by about 7 times with 2 swaps without using pypy
- Automatic game board capturing, with nearly 100% accuracy using paddle ocr and some preprocessing
- Implemented into app with simple GUI, guiding arrows, automatic window tracking by title

## How to use?
- It's pretty much self-explanatory, you just have to run start.bat, wait for the app to finish initializing, select window that the game will be played in, though I already enabled auto track window with title contains "Discord" by default, so if you're not playing in pop-out mode, the only think you have to do is to select the number of swap, then click capture.  
- Oh, and don't forget to make the game window as big as possible, like if you're in voice chat, hide voice users, if you're in DM voice calling, hide chat
