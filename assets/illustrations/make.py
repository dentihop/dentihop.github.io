import os

this_dir = os.getcwd()

with open("corresp.txt", "w", encoding="utf-8") as out:
    for dirpath, dirnames, filenames in os.walk(this_dir):
        out.write(dirpath[len(this_dir) + 1:] + ":" + str(filenames)+"\n")
        
        for filename in filenames:
            print(dirpath[len(this_dir) + 1:], filename)
