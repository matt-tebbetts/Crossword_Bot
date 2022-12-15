


msg_txt = """boxofficega.me
March 12, 2004
✅ 160
✅ 160
✅ 120
✅ 160
✅ 80
➕ 20
🏆 700
"""

game_dtl = msg_txt.split('\n')[1]
trophy_symbol = u'\U0001f3c6'
for line in msg_txt.split('\n'):
    if line.find(trophy_symbol) >= 0:
        score = line.split(' ')[1]

print(score)