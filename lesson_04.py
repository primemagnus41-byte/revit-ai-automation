def xona_tekshir(nom,yuzasi):
    if yuzasi >=20:
         print(f"{nom}: ✅ Norma bajarildi ({yuzasi} m²)")
    else:
         print(f"{nom}:❌ Norma bajarilmadi ({yuzasi}m²)")

xona_tekshir("Yotoqxona",20)
xona_tekshir("Mehmonxona",42)
xona_tekshir("OShxona",12)