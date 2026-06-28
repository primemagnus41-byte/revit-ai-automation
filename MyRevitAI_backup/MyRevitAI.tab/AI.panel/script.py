# -*- coding: utf-8 -*-
from pyrevit import forms
from pyrevit import output
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import *
from Autodesk.Revit.DB import UnitUtils, UnitTypeId
import json
import clr
clr.AddReference("System.Net")
from System.Net import WebClient
from System.Collections.Generic import List
from config import API_KEY

doc = __revit__.ActiveUIDocument.Document

def metr(qiymat):
    return UnitUtils.ConvertToInternalUnits(qiymat, UnitTypeId.Meters)

def mm(qiymat):
    return UnitUtils.ConvertToInternalUnits(qiymat, UnitTypeId.Millimeters)

def kub_metr(qiymat):
    return UnitUtils.ConvertFromInternalUnits(qiymat, UnitTypeId.CubicMeters)

def normalla(s):
    s = s.lower()
    s = s.replace(u"х", u"x")
    s = s.replace(u" ", u"")
    return s

def claude_ga_soru(tarix, yangi_buyruq):
    client = WebClient()
    client.Headers.Add("Content-Type", "application/json")
    client.Headers.Add("x-api-key", API_KEY)
    client.Headers.Add("anthropic-version", "2023-06-01")
    
    # Suhbat tarixini qoshish
    xabarlar = []
    for x in tarix:
        xabarlar.append({"role": x["rol"], "content": x["matn"]})
    xabarlar.append({"role": "user", "content": yangi_buyruq})
    
    data = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "system": "Sen Revit AI assistantisan. Faqat sof JSON formatda javob ber, ``` ishlatma. MUHIM: agar foydalanuvchi 'hisobot', 'spetsifikatsiya', 'hajm', 'hisob', 'chiqar' desa - faqat {\"amal\": \"hisobot\"} deb javob ber. Boshqa hollarda karkas format: {\"amal\": \"karkas\", \"eni\": 18, \"uzunligi\": 24, \"qadam\": 6, \"qavatlar\": 3, \"qavat_balandligi\": 3, \"kolonna_olcham\": \"400x400\", \"balka_olcham\": \"400x400\", \"plita\": \"monolit\", \"plita_qalinligi\": 200, \"material\": \"beton\"}. Eni, uzunligi, qadam, qavat_balandligi metrda. Olchamlar mm da. Plita: monolit yoki pk, kerak bolmasa \"\". Agar aytilmasa: qadam 0, qavatlar 1, qavat_balandligi 3, olchamlar \"\", plita \"\", plita_qalinligi 200, material \"\".",
        "messages": xabarlar
    })
    
    response = client.UploadString("https://api.anthropic.com/v1/messages", data)
    result = json.loads(response)
    return result["content"][0]["text"]

def olcham_ajrat(olcham):
    s = normalla(olcham)
    qismlar = s.split(u"x")
    if len(qismlar) == 2:
        try:
            return float(qismlar[0]), float(qismlar[1])
        except:
            return None
    return None

def tur_olchamini_ornat(symbol, kenglik_mm, balandlik_mm):
    kenglik_nomlar = [u"b", u"B", u"Ширина", u"ширина", u"ADSK_Размер_Ширина", u"Width"]
    balandlik_nomlar = [u"h", u"H", u"Высота", u"высота", u"ADSK_Размер_Высота", u"Height"]
    k_ok = False
    for nom in kenglik_nomlar:
        p = symbol.LookupParameter(nom)
        if p and not p.IsReadOnly:
            p.Set(mm(kenglik_mm))
            k_ok = True
            break
    b_ok = False
    for nom in balandlik_nomlar:
        p = symbol.LookupParameter(nom)
        if p and not p.IsReadOnly:
            p.Set(mm(balandlik_mm))
            b_ok = True
            break
    return k_ok and b_ok

def family_tur_top(family, nom):
    ids = family.GetFamilySymbolIds()
    for fid in ids:
        s = doc.GetElement(fid)
        if Element.Name.GetValue(s) == nom:
            return s
    return None

def olcham_taminla(symbol, olcham):
    o = olcham_ajrat(olcham)
    if not o:
        return symbol
    kenglik, balandlik = o
    olcham_n = normalla(olcham)
    nomi = normalla(symbol.Family.Name + " " + Element.Name.GetValue(symbol))
    if olcham_n in nomi:
        return symbol
    yangi_nom = olcham + " (AI)"
    mavjud = family_tur_top(symbol.Family, yangi_nom)
    if mavjud:
        return mavjud
    try:
        yangi = symbol.Duplicate(yangi_nom)
        tur_olchamini_ornat(yangi, kenglik, balandlik)
        return yangi
    except:
        return symbol

def balka_kengligi(b_symbol, b_olcham):
    o = olcham_ajrat(b_olcham) if b_olcham else None
    if o:
        return mm(o[0])
    for nom in [u"b", u"B", u"Ширина", u"ADSK_Размер_Ширина", u"Width"]:
        p = b_symbol.LookupParameter(nom)
        if p:
            try:
                v = p.AsDouble()
                if v > 0:
                    return v
            except:
                pass
    return mm(300)

def kolonna_top(olcham, material):
    collector = FilteredElementCollector(doc)
    collector.OfCategory(BuiltInCategory.OST_StructuralColumns)
    collector.OfClass(FamilySymbol)
    hammasi = list(collector)
    if not hammasi:
        return None
    olcham_n = normalla(olcham) if olcham else ""
    for s in hammasi:
        nomi = normalla(s.Family.Name + " " + Element.Name.GetValue(s))
        mos = True
        if olcham_n and olcham_n not in nomi:
            mos = False
        if material == "metall" and not any(x in nomi for x in [u"сталь", u"steel", u"металл", u"двутавр", u"швеллер"]):
            mos = False
        if mos:
            return s
    for s in hammasi:
        nomi = normalla(s.Family.Name + " " + Element.Name.GetValue(s))
        if u"прямоуг" in nomi:
            return s
    return hammasi[0]

def balka_top(olcham):
    collector = FilteredElementCollector(doc)
    collector.OfCategory(BuiltInCategory.OST_StructuralFraming)
    collector.OfClass(FamilySymbol)
    hammasi = list(collector)
    if not hammasi:
        return None
    olcham_n = normalla(olcham) if olcham else ""
    for s in hammasi:
        nomi = normalla(s.Family.Name + " " + Element.Name.GetValue(s))
        if u"прямоуг" in nomi and (not olcham_n or olcham_n in nomi):
            return s
    for s in hammasi:
        nomi = normalla(s.Family.Name + " " + Element.Name.GetValue(s))
        if u"прямоуг" in nomi:
            return s
    return hammasi[0]

def plita_top(qalinligi, turi):
    collector = FilteredElementCollector(doc)
    collector.OfClass(FloorType)
    hammasi = []
    for ft in collector:
        try:
            if ft.IsFoundationSlab:
                continue
        except:
            pass
        hammasi.append(ft)
    if not hammasi:
        return None
    q_str = str(int(qalinligi))
    for ft in hammasi:
        nomi = normalla(Element.Name.GetValue(ft))
        if u"перекрыт" not in nomi:
            continue
        tur_mos = True
        if turi == "pk" and not (u"пк" in nomi or u"пустот" in nomi):
            tur_mos = False
        if turi == "monolit" and (u"пк" in nomi or u"пустот" in nomi):
            tur_mos = False
        if tur_mos and q_str in nomi:
            return ft
    for ft in hammasi:
        nomi = normalla(Element.Name.GetValue(ft))
        tur_mos = True
        if turi == "pk" and not (u"пк" in nomi or u"пустот" in nomi):
            tur_mos = False
        if turi == "monolit" and (u"пк" in nomi or u"пустот" in nomi):
            tur_mos = False
        if tur_mos and q_str in nomi:
            return ft
    for ft in hammasi:
        nomi = normalla(Element.Name.GetValue(ft))
        if q_str in nomi:
            return ft
    return hammasi[0]

def kolonna_yarat(nuqta, symbol, level, past_r, tepa_r):
    inst = doc.Create.NewFamilyInstance(nuqta, symbol, level, StructuralType.Column)
    top_param = inst.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM)
    if top_param:
        top_param.Set(tepa_r)
    top_level = inst.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)
    if top_level:
        top_level.Set(level.Id)
    if top_param:
        top_param.Set(tepa_r)
    base_level = inst.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)
    if base_level:
        base_level.Set(level.Id)
    base_offset = inst.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM)
    if base_offset:
        base_offset.Set(past_r)
    return inst

def balka_yarat(boshi, oxiri, symbol, level):
    line = Line.CreateBound(boshi, oxiri)
    inst = doc.Create.NewFamilyInstance(line, symbol, level, StructuralType.Beam)
    yj = inst.get_Parameter(BuiltInParameter.Y_JUSTIFICATION)
    if yj:
        yj.Set(1)
    return inst

def plita_panel_yarat(x1, y1, x2, y2, z, floor_type, level):
    p1 = XYZ(x1, y1, 0)
    p2 = XYZ(x2, y1, 0)
    p3 = XYZ(x2, y2, 0)
    p4 = XYZ(x1, y2, 0)
    loop = CurveLoop()
    loop.Append(Line.CreateBound(p1, p2))
    loop.Append(Line.CreateBound(p2, p3))
    loop.Append(Line.CreateBound(p3, p4))
    loop.Append(Line.CreateBound(p4, p1))
    loops = List[CurveLoop]()
    loops.Add(loop)
    plita = Floor.Create(doc, loops, floor_type.Id, level.Id)
    offset = plita.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)
    if offset:
        offset.Set(z)
    return plita

def hajm_yigindi(kategoriya):
    collector = FilteredElementCollector(doc)
    collector.OfCategory(kategoriya)
    collector.WhereElementIsNotElementType()
    soni = 0
    hajm = 0.0
    for el in collector:
        p = el.get_Parameter(BuiltInParameter.HOST_VOLUME_COMPUTED)
        if p:
            v = p.AsDouble()
            if v > 0:
                hajm += v
                soni += 1
    return soni, kub_metr(hajm)

def hisobot_chiqar():
    k_soni, k_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralColumns)
    b_soni, b_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralFraming)
    p_soni, p_hajm = hajm_yigindi(BuiltInCategory.OST_Floors)
    f_soni, f_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralFoundation)
    jami = k_hajm + b_hajm + p_hajm + f_hajm
    out = output.get_output()
    out.close_others()
    out.set_title("Revit AI - Beton Spetsifikatsiyasi")
    out.print_md("# BETON SPETSIFIKATSIYASI")
    out.print_md("---")
    sarlavha = ["No", "Element", "Soni", "Hajm (m3)", "Ulush (%)"]
    qatorlar = []
    if k_soni > 0:
        qatorlar.append(["1", "Kolonnalar", str(k_soni) + " ta", str(round(k_hajm, 3)), str(round(k_hajm / jami * 100, 1)) + "%"])
    if b_soni > 0:
        qatorlar.append(["2", "Balkalar", str(b_soni) + " ta", str(round(b_hajm, 3)), str(round(b_hajm / jami * 100, 1)) + "%"])
    if p_soni > 0:
        qatorlar.append(["3", "Plitalar", str(p_soni) + " ta", str(round(p_hajm, 3)), str(round(p_hajm / jami * 100, 1)) + "%"])
    if f_soni > 0:
        qatorlar.append(["4", "Fundamentlar", str(f_soni) + " ta", str(round(f_hajm, 3)), str(round(f_hajm / jami * 100, 1)) + "%"])
    qatorlar.append(["", "JAMI BETON", "", str(round(jami, 3)), "100%"])
    out.print_table(qatorlar, title="Beton elementlari", columns=sarlavha)
    out.print_md("---")
    out.print_md("## JAMI: " + str(round(jami, 3)) + " m3")

def karkas_qur(eni, uzunligi, qadam, qavatlar, qavat_h, k_olcham, b_olcham, plita, plita_q, material):
    k_symbol = kolonna_top(k_olcham, material)
    b_symbol = balka_top(b_olcham)
    if not k_symbol:
        forms.alert("Kolonna family topilmadi!")
        return
    if not b_symbol:
        forms.alert("Balka family topilmadi!")
        return
    f_type = None
    if plita:
        f_type = plita_top(plita_q, plita)
        if not f_type:
            forms.alert("Plita turi topilmadi!")
            return
    level = doc.ActiveView.GenLevel
    if qadam and qadam > 0:
        bays_x = max(1, int(round(eni / float(qadam))))
        bays_y = max(1, int(round(uzunligi / float(qadam))))
    else:
        bays_x = 1
        bays_y = 1
    sx = eni / float(bays_x)
    sy = uzunligi / float(bays_y)
    t = Transaction(doc, "AI Bino")
    t.Start()
    if k_olcham:
        k_symbol = olcham_taminla(k_symbol, k_olcham)
    if b_olcham:
        b_symbol = olcham_taminla(b_symbol, b_olcham)
    k_symbol.Activate()
    b_symbol.Activate()
    bk = balka_kengligi(b_symbol, b_olcham)
    yarim = bk / 2.0
    kolonna_soni = 0
    balka_soni = 0
    plita_soni = 0
    balkalar = []
    for qavat in range(qavatlar):
        z_past = metr(qavat * qavat_h)
        z_tepa = metr((qavat + 1) * qavat_h)
        for i in range(bays_x + 1):
            for j in range(bays_y + 1):
                nuqta = XYZ(metr(i * sx), metr(j * sy), 0)
                kolonna_yarat(nuqta, k_symbol, level, z_past, z_tepa)
                kolonna_soni += 1
        for j in range(bays_y + 1):
            for i in range(bays_x):
                b = balka_yarat(XYZ(metr(i * sx), metr(j * sy), z_tepa), XYZ(metr((i + 1) * sx), metr(j * sy), z_tepa), b_symbol, level)
                balkalar.append((b, z_tepa))
                balka_soni += 1
        for i in range(bays_x + 1):
            for j in range(bays_y):
                b = balka_yarat(XYZ(metr(i * sx), metr(j * sy), z_tepa), XYZ(metr(i * sx), metr((j + 1) * sy), z_tepa), b_symbol, level)
                balkalar.append((b, z_tepa))
                balka_soni += 1
        if f_type:
            for i in range(bays_x):
                for j in range(bays_y):
                    x1 = metr(i * sx) + yarim
                    y1 = metr(j * sy) + yarim
                    x2 = metr((i + 1) * sx) - yarim
                    y2 = metr((j + 1) * sy) - yarim
                    if x2 > x1 and y2 > y1:
                        plita_panel_yarat(x1, y1, x2, y2, z_tepa, f_type, level)
                        plita_soni += 1
    doc.Regenerate()
    for inst, z in balkalar:
        bb = inst.get_BoundingBox(None)
        if bb:
            farq = z - bb.Max.Z
            if abs(farq) > 0.00001:
                ElementTransformUtils.MoveElement(doc, inst.Id, XYZ(0, 0, farq))
    t.Commit()
    k_nomi = Element.Name.GetValue(k_symbol)
    b_nomi = Element.Name.GetValue(b_symbol)
    xabar = "Bino qurildi!\n"
    xabar += "Qavatlar: " + str(qavatlar) + "\n"
    xabar += "Kolonnalar: " + str(kolonna_soni) + " ta (" + k_nomi + ")\n"
    xabar += "Balkalar: " + str(balka_soni) + " ta (" + b_nomi + ")\n"
    xabar += "Setka qadami: " + str(round(sx, 2)) + " x " + str(round(sy, 2)) + " m\n"
    if f_type:
        xabar += "Plita panellari: " + str(plita_soni) + " ta\n"
    xabar += "Olcham: " + str(eni) + "x" + str(uzunligi) + " m"
    forms.alert(xabar, title="Revit AI")

# Suhbat tarixini saqlash
suhbat_tarixi = []

# Doimiy suhbat
while True:
    buyruq = forms.ask_for_string(prompt="Buyruq bering (Bekor qilish uchun Cancel):", title="Revit AI Chat")
    
    if not buyruq:
        break
    
    suhbat_tarixi.append({"rol": "user", "matn": buyruq})
    
    javob = claude_ga_soru(suhbat_tarixi, buyruq)
    toza = javob.replace("```json", "").replace("```", "").strip()
    
    try:
        ma_lumot = json.loads(toza)
        amal = ma_lumot["amal"]
        
        if amal == "karkas":
            karkas_qur(
                ma_lumot["eni"],
                ma_lumot["uzunligi"],
                ma_lumot.get("qadam", 0),
                ma_lumot.get("qavatlar", 1),
                ma_lumot.get("qavat_balandligi", 3),
                ma_lumot.get("kolonna_olcham", ""),
                ma_lumot.get("balka_olcham", ""),
                ma_lumot.get("plita", ""),
                ma_lumot.get("plita_qalinligi", 200),
                ma_lumot.get("material", "")
            )
            suhbat_tarixi.append({"rol": "assistant", "matn": "Karkas qurildi!"})
        
        elif amal == "hisobot":
            hisobot_chiqar()
            suhbat_tarixi.append({"rol": "assistant", "matn": "Spetsifikatsiya chiqarildi!"})
    
    except:
        forms.alert(javob, title="AI javobi")
        suhbat_tarixi.append({"rol": "assistant", "matn": javob})