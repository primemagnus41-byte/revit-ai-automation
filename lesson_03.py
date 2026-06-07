xonalar=[
{"nom":"Yotoqxona","eni":4,"uzunligi":5},
{"nom":"Mehmonxona","eni":6,"uzunligi":7},
{"nom":"Oshxona","eni":3,"uzunligi":4},
]
def xona_yuzasi(eni,uzunligi):
    return eni*uzunligi
for xona in xonalar:
    yuzasi=xona_yuzasi(xona["eni"],xona["uzunligi"])
    print(f"{xona['nom']}:{yuzasi}m²")
