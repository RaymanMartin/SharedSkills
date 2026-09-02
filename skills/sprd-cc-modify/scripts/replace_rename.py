import re
import os

file = "test.txt"
with open(file, "r", encoding="u8") as fp:
    lines = fp.readlines()
    with open(file, "w", encoding="u8") as fw:
        num = 0
        for line in lines:
            pattern = re.compile(r'\d{2,}[a-z]{1}\d{1}:|\d{2,}:')
            line = line.replace((pattern.findall(line))[0], '')
            line = line[0:-10]
            line = line.replace(' ', ',-')
            line = line.replace('-', '0x')
            line = line.replace(',', ', ')
            line = line[2:-3]
            num += 1
            if num == 1:
                fw.write("/* Seth Forshee's regdb certificate */\n" + line + "\n")
            elif num == len(lines):
                line = line.replace(', 0x', '')
                pattern = re.compile('.{2}')
                line = ', 0x'.join(pattern.findall(line))
                line = line.replace('0x, ', '')
                fw.write(line + ',' + "\n")
            else:
                fw.write(line + "\n")
os.rename("test.txt", "wens.hex")
