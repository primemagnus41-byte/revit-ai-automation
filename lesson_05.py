xonalar = [
    {"nom":"Yotoqxona","eni":4,"uzunligi":5},
    {"nom":"Mehmonxona","eni": 6,"uzunligi":7},
    {"nom":"Oshxona","eni":3,"uzunligi":4},
]

def xona_yuzasi(eni,uzunligi):
    return eni*uzunligi

def norma_tekshir(nom,yuzasi):
    if yuzasi>=20:
        print(f"{nom}:✅{yuzasi} m²-Norma OK")
    else:
        print(f"{nom}:❌{yuzasi} m²-Norma bajarilmadi")

for xona in xonalar:
    yuzasi=xona_yuzasi(xona["eni"],xona["uzunligi"])
    norma_tekshir(xona["nom"],yuzasi)