# -*- coding: utf-8 -*-
from pyrevit import forms, output
import clr, os
from datetime import datetime
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')
import wpf
from System.Windows import Window, Visibility
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import *
from Autodesk.Revit.DB import UnitUtils, UnitTypeId, WallUtils
from System.Collections.Generic import List
from config import API_KEY

doc = __revit__.ActiveUIDocument.Document

def metr(v): return UnitUtils.ConvertToInternalUnits(v, UnitTypeId.Meters)
def mm(v): return UnitUtils.ConvertToInternalUnits(v, UnitTypeId.Millimeters)
def kub_metr(v): return UnitUtils.ConvertFromInternalUnits(v, UnitTypeId.CubicMeters)
def normalla(s): return s.lower().replace(u"х", u"x").replace(u" ", u"")

def level_top():
    level = doc.ActiveView.GenLevel
    if level is None:
        collector = FilteredElementCollector(doc).OfClass(Level)
        levels = sorted(list(collector), key=lambda l: l.Elevation)
        if levels: return levels[0]
    return level

# ===== TYPE YARATISH =====
def floor_type_kerakli(qalinligi_mm, nom_prefix):
    nom = nom_prefix + "_" + str(int(qalinligi_mm)) + "mm_AI"
    col = FilteredElementCollector(doc).OfClass(FloorType)
    for ft in col:
        if Element.Name.GetValue(ft) == nom: return ft
    asos = None
    beton_asos = None
    kalit = [u"монолит", u"железобетон", u"жб", u"бетон", u"b25", u"b20"]
    col2 = FilteredElementCollector(doc).OfClass(FloorType)
    for ft in col2:
        nm = normalla(Element.Name.GetValue(ft))
        if u"пк" in nm or u"пустот" in nm: continue
        try:
            if ft.IsFoundationSlab: continue
        except: pass
        if asos is None: asos = ft
        for k in kalit:
            if k in nm: beton_asos = ft; break
        if beton_asos: break
    base = beton_asos if beton_asos else asos
    if not base: return None
    try:
        yangi = base.Duplicate(nom)
        cs = yangi.GetCompoundStructure()
        if cs:
            idx = -1
            for i in range(cs.LayerCount):
                if cs.GetLayerFunction(i) == MaterialFunctionAssignment.Structure:
                    idx = i; break
            if idx >= 0:
                cs.SetLayerWidth(idx, mm(qalinligi_mm))
                for i in range(cs.LayerCount):
                    if i != idx:
                        try: cs.SetLayerWidth(i, 0)
                        except: pass
            yangi.SetCompoundStructure(cs)
        return yangi
    except: return base

def wall_type_beton(eni_mm):
    nom = "Beton_" + str(int(eni_mm)) + "mm_AI"
    col = FilteredElementCollector(doc).OfClass(WallType)
    for wt in col:
        if Element.Name.GetValue(wt) == nom: return wt
    asos = None
    beton_asos = None
    kalit = [u"монолит", u"железобетон", u"жб", u"бетон", u"b25", u"b20", u"concrete"]
    col2 = FilteredElementCollector(doc).OfClass(WallType)
    for wt in col2:
        if wt.Kind != WallKind.Basic: continue
        nm = normalla(Element.Name.GetValue(wt))
        if asos is None: asos = wt
        for k in kalit:
            if k in nm: beton_asos = wt; break
        if beton_asos: break
    base = beton_asos if beton_asos else asos
    if not base: return None
    try:
        yangi = base.Duplicate(nom)
        cs = yangi.GetCompoundStructure()
        if cs:
            idx = -1
            for i in range(cs.LayerCount):
                if cs.GetLayerFunction(i) == MaterialFunctionAssignment.Structure:
                    idx = i; break
            if idx >= 0:
                cs.SetLayerWidth(idx, mm(eni_mm))
                for i in range(cs.LayerCount):
                    if i != idx:
                        try: cs.SetLayerWidth(i, 0)
                        except: pass
            yangi.SetCompoundStructure(cs)
        return yangi
    except: return base

# ===== FAMILY IZLASH =====
def kolonna_top(olcham):
    col = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_StructuralColumns).OfClass(FamilySymbol)
    hammasi = list(col)
    if not hammasi: return None
    if olcham:
        on = normalla(olcham)
        for s in hammasi:
            if on in normalla(s.Family.Name + Element.Name.GetValue(s)): return s
    for s in hammasi:
        if u"прямоуг" in normalla(s.Family.Name): return s
    return hammasi[0]

def balka_top(olcham):
    col = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_StructuralFraming).OfClass(FamilySymbol)
    hammasi = list(col)
    if not hammasi: return None
    if olcham:
        on = normalla(olcham)
        for s in hammasi:
            nm = normalla(s.Family.Name + Element.Name.GetValue(s))
            if u"прямоуг" in nm and on in nm: return s
    for s in hammasi:
        if u"прямоуг" in normalla(s.Family.Name): return s
    return hammasi[0]

def cont_footing_top():
    col = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_StructuralFoundation).OfClass(FamilySymbol)
    hammasi = list(col)
    if not hammasi:
        # ElementType orqali ham qidirish
        col2 = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_StructuralFoundation).WhereElementIsElementType()
        hammasi = list(col2)
    if not hammasi: return None
    kalit = [u"ленточн", u"непрерыв", u"strip", u"continuous", u"cont", u"фундамент"]
    for ft in hammasi:
        try:
            nm = normalla(ft.Family.Name + Element.Name.GetValue(ft))
            for k in kalit:
                if k in nm: return ft
        except:
            try:
                nm = normalla(Element.Name.GetValue(ft))
                for k in kalit:
                    if k in nm: return ft
            except: pass
    return hammasi[0] if hammasi else None

# ===== OLCHAM TAMINLASH =====
def olcham_ajrat(s):
    parts = normalla(s).split("x")
    if len(parts) == 2:
        try: return float(parts[0]), float(parts[1])
        except: return None
    return None

def family_tur_top(family, nom):
    for fid in family.GetFamilySymbolIds():
        s = doc.GetElement(fid)
        if Element.Name.GetValue(s) == nom: return s
    return None

def parametr_ornat(symbol, kenglik_mm, balandlik_mm):
    k_ok = False
    b_ok = False
    keng_kalit = [u"ADSK_Размер_Ширина", u"Ширина", u"ширина", u"b", u"B", u"Width", u"width"]
    baland_kalit = [u"ADSK_Размер_Высота", u"Высота", u"высота", u"h", u"H", u"Height", u"height", u"Depth"]
    # Barcha parametrlarni ko'rib chiqish
    for p in symbol.Parameters:
        if p.IsReadOnly: continue
        if p.StorageType != StorageType.Double: continue
        pname = p.Definition.Name
        if not k_ok:
            for nom in keng_kalit:
                if pname == nom:
                    try: p.Set(mm(kenglik_mm)); k_ok = True; break
                    except: pass
        if not b_ok:
            for nom in baland_kalit:
                if pname == nom:
                    try: p.Set(mm(balandlik_mm)); b_ok = True; break
                    except: pass
    return k_ok and b_ok

def olcham_taminla(symbol, olcham):
    o = olcham_ajrat(olcham)
    if not o: return symbol
    kenglik, balandlik = o
    if normalla(olcham) in normalla(symbol.Family.Name + Element.Name.GetValue(symbol)): return symbol
    yangi_nom = olcham + " (AI)"
    mavjud = family_tur_top(symbol.Family, yangi_nom)
    if mavjud: return mavjud
    try:
        yangi = symbol.Duplicate(yangi_nom)
        parametr_ornat(yangi, kenglik, balandlik)
        return yangi
    except: return symbol

def balka_kengligi(symbol, olcham):
    o = olcham_ajrat(olcham)
    if o: return mm(o[0])
    for nom in [u"b", u"B", u"Ширина", u"Ширина сечения", u"Width"]:
        p = symbol.LookupParameter(nom)
        if p:
            try:
                v = p.AsDouble()
                if v > 0: return v
            except: pass
    return mm(300)

# ===== ELEMENT YARATISH =====
def kolonna_yarat(nuqta, symbol, level, past_r, tepa_r):
    inst = doc.Create.NewFamilyInstance(nuqta, symbol, level, StructuralType.Column)
    tp = inst.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM)
    if tp: tp.Set(tepa_r)
    tl = inst.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)
    if tl: tl.Set(level.Id)
    if tp: tp.Set(tepa_r)
    bl = inst.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)
    if bl: bl.Set(level.Id)
    bo = inst.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM)
    if bo: bo.Set(past_r)
    return inst

def balka_yarat(boshi, oxiri, symbol, level):
    line = Line.CreateBound(boshi, oxiri)
    inst = doc.Create.NewFamilyInstance(line, symbol, level, StructuralType.Beam)
    yj = inst.get_Parameter(BuiltInParameter.Y_JUSTIFICATION)
    if yj: yj.Set(1)
    return inst

def plita_panel_yarat(x1, y1, x2, y2, z, floor_type, level):
    if abs(x2-x1) < 0.001 or abs(y2-y1) < 0.001: return None
    loop = CurveLoop()
    pts = [XYZ(x1,y1,0), XYZ(x2,y1,0), XYZ(x2,y2,0), XYZ(x1,y2,0)]
    for i in range(4): loop.Append(Line.CreateBound(pts[i], pts[(i+1)%4]))
    loops = List[CurveLoop](); loops.Add(loop)
    plita = Floor.Create(doc, loops, floor_type.Id, level.Id)
    off = plita.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)
    if off: off.Set(z)
    return plita

def floor_element_yarat(ax1, ay1, ax2, ay2, z, ft, level):
    if abs(ax2-ax1) < 0.001 or abs(ay2-ay1) < 0.001: return
    loop = CurveLoop()
    pts = [XYZ(metr(ax1),metr(ay1),0), XYZ(metr(ax2),metr(ay1),0), XYZ(metr(ax2),metr(ay2),0), XYZ(metr(ax1),metr(ay2),0)]
    for i in range(4): loop.Append(Line.CreateBound(pts[i], pts[(i+1)%4]))
    loops = List[CurveLoop](); loops.Add(loop)
    try:
        pl = Floor.Create(doc, loops, ft.Id, level.Id)
        off = pl.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)
        if off: off.Set(z)
    except: pass

# ===== FUNDAMENT =====
def lenta_fundament_qur(eni, uzunligi, qadam, pod_eni, pod_qalin, lenta_eni_mm, lenta_baland, x0, y0, level):
    # Lenta uchun devor type
    wt_lenta = wall_type_beton(lenta_eni_mm)
    # Podushka uchun devor type (kengroq!)
    wt_pod = wall_type_beton(pod_eni)
    if not wt_lenta: return

    if qadam and qadam > 0:
        bays_x = max(1, int(round(eni / float(qadam))))
        bays_y = max(1, int(round(uzunligi / float(qadam))))
    else:
        bays_x = 1; bays_y = 1
    sx = eni / float(bays_x)
    sy = uzunligi / float(bays_y)

    # Devor chiziqlari — ikkala qism uchun bir xil
    wall_lines = []
    wall_lines.append((XYZ(metr(x0),metr(y0),0), XYZ(metr(x0+eni),metr(y0),0)))
    wall_lines.append((XYZ(metr(x0+eni),metr(y0),0), XYZ(metr(x0+eni),metr(y0+uzunligi),0)))
    wall_lines.append((XYZ(metr(x0+eni),metr(y0+uzunligi),0), XYZ(metr(x0),metr(y0+uzunligi),0)))
    wall_lines.append((XYZ(metr(x0),metr(y0+uzunligi),0), XYZ(metr(x0),metr(y0),0)))
    for j in range(1, bays_y):
        y = y0 + j * sy
        wall_lines.append((XYZ(metr(x0),metr(y),0), XYZ(metr(x0+eni),metr(y),0)))
    for i in range(1, bays_x):
        x = x0 + i * sx
        wall_lines.append((XYZ(metr(x),metr(y0),0), XYZ(metr(x),metr(y0+uzunligi),0)))

    # 1. PODUSHKA — pastda, kengroq devor
    pod_h = metr(pod_qalin / 1000.0)
    pod_off = metr(-(lenta_baland + pod_qalin) / 1000.0)
    pod_devorlar = []
    if wt_pod:
        for (p1, p2) in wall_lines:
            try:
                line = Line.CreateBound(p1, p2)
                w = Wall.Create(doc, line, wt_pod.Id, level.Id, pod_h, pod_off, False, True)
                pod_devorlar.append(w)
            except: pass
        doc.Regenerate()
        for w in pod_devorlar:
            try:
                WallUtils.AllowWallJoinAtEnd(w, 0)
                WallUtils.AllowWallJoinAtEnd(w, 1)
            except: pass

    # 2. LENTA — podushka ustida
    lenta_h = metr(lenta_baland / 1000.0)
    lenta_off = metr(-lenta_baland / 1000.0)
    lenta_devorlar = []
    for (p1, p2) in wall_lines:
        try:
            line = Line.CreateBound(p1, p2)
            w = Wall.Create(doc, line, wt_lenta.Id, level.Id, lenta_h, lenta_off, False, True)
            lenta_devorlar.append(w)
        except: pass
    doc.Regenerate()
    for w in lenta_devorlar:
        try:
            WallUtils.AllowWallJoinAtEnd(w, 0)
            WallUtils.AllowWallJoinAtEnd(w, 1)
        except: pass

# ===== OS CHIZIQLARI =====
def osi_qur(eni, uzunligi, qadam, x0, y0):
    if qadam and qadam > 0:
        bays_x = max(1, int(round(eni / float(qadam))))
        bays_y = max(1, int(round(uzunligi / float(qadam))))
    else:
        bays_x = 1; bays_y = 1
    sx = eni / float(bays_x); sy = uzunligi / float(bays_y)
    uzat = 2.0
    for i in range(bays_x + 1):
        x = x0 + i * sx
        line = Line.CreateBound(XYZ(metr(x),metr(y0-uzat),0), XYZ(metr(x),metr(y0+uzunligi+uzat),0))
        try:
            g = Grid.Create(doc, line); g.Name = str(i+1)
        except: pass
    harflar = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for j in range(bays_y + 1):
        y = y0 + j * sy
        line = Line.CreateBound(XYZ(metr(x0-uzat),metr(y),0), XYZ(metr(x0+eni+uzat),metr(y),0))
        try:
            g = Grid.Create(doc, line)
            if j < len(harflar): g.Name = harflar[j]
        except: pass

# ===== ASOSIY QURILISH =====
def bino_qur(p, progress_cb=None):
    eni = p["eni"]; uzunligi = p["uzunligi"]
    qadam = p["qadam"]; qavatlar = p["qavatlar"]
    qavat_h = p["qavat_h"]
    x0 = p["x0"]; y0 = p["y0"]
    k_symbol = kolonna_top(p["k_olcham"])
    b_symbol = balka_top(p["b_olcham"])
    if not k_symbol: forms.alert("Kolonna family topilmadi!"); return False
    if not b_symbol: forms.alert("Balka family topilmadi!"); return False
    f_type = None
    if p["plita_kerak"]:
        f_type = floor_type_kerakli(p["plita_q"], "Perekritie")
    level = level_top()
    if not level: forms.alert("Level topilmadi!"); return False
    if qadam and qadam > 0:
        bays_x = max(1, int(round(eni / float(qadam))))
        bays_y = max(1, int(round(uzunligi / float(qadam))))
    else:
        bays_x = 1; bays_y = 1
    sx = eni / float(bays_x); sy = uzunligi / float(bays_y)

    t = Transaction(doc, "AI Bino")
    t.Start()

    k_symbol = olcham_taminla(k_symbol, p["k_olcham"])
    b_symbol = olcham_taminla(b_symbol, p["b_olcham"])
    k_symbol.Activate(); b_symbol.Activate()

    # Perekritie ofseti - kolonna va balkadan kattasi
    b_o = olcham_ajrat(p["b_olcham"])
    k_o = olcham_ajrat(p["k_olcham"])
    b_yarim = mm(b_o[0] / 2.0) if b_o else balka_kengligi(b_symbol, p["b_olcham"])
    k_yarim = mm(k_o[0] / 2.0) if k_o else b_yarim
    slab_offset = b_yarim

    balkalar = []

    # 1. Fundament
    if p["fund_kerak"]:
        if progress_cb: progress_cb(10, "Fundament qurilmoqda...")
        if p["fund_turi"] == "lenta":
            lenta_fundament_qur(eni, uzunligi, qadam, p["pod_eni"], p["pod_qalin"], p["lenta_eni"], p["lenta_baland"], x0, y0, level)
        else:
            monolit_fundament_qur(eni, uzunligi, p["monolit_chiqish"], p["monolit_qalin"], x0, y0, level)

    # 2. Os chiziqlari
    if p["osi_kerak"]:
        if progress_cb: progress_cb(25, "Os chiziqlari...")
        osi_qur(eni, uzunligi, qadam, x0, y0)

    # 3. Kolonnalar
    if progress_cb: progress_cb(40, "Kolonnalar...")
    for qavat in range(qavatlar):
        z_past = metr(qavat * qavat_h)
        z_tepa = metr((qavat + 1) * qavat_h)
        for i in range(bays_x + 1):
            for j in range(bays_y + 1):
                nuqta = XYZ(metr(x0+i*sx), metr(y0+j*sy), 0)
                kolonna_yarat(nuqta, k_symbol, level, z_past, z_tepa)

    # 4. Balkalar
    if progress_cb: progress_cb(60, "Balkalar...")
    for qavat in range(qavatlar):
        z_tepa = metr((qavat + 1) * qavat_h)
        for j in range(bays_y + 1):
            for i in range(bays_x):
                b = balka_yarat(XYZ(metr(x0+i*sx),metr(y0+j*sy),z_tepa), XYZ(metr(x0+(i+1)*sx),metr(y0+j*sy),z_tepa), b_symbol, level)
                balkalar.append((b, z_tepa))
        for i in range(bays_x + 1):
            for j in range(bays_y):
                b = balka_yarat(XYZ(metr(x0+i*sx),metr(y0+j*sy),z_tepa), XYZ(metr(x0+i*sx),metr(y0+(j+1)*sy),z_tepa), b_symbol, level)
                balkalar.append((b, z_tepa))

    # 5. Plita
    if f_type and p["plita_kerak"]:
        if progress_cb: progress_cb(80, "Perekritie...")
        plita_turi = p["plita_turi"]
        
        for qavat in range(qavatlar):
            z_tepa = metr((qavat + 1) * qavat_h)
            
            if plita_turi == "pk":
                # ===== PK PUSTOTNIY PLITA =====
                pk_eni = p.get("pk_eni", 1200) / 1000.0  # metrga
                tayanchiq = p.get("tayanchiq", 130) / 1000.0  # metrga
                
                for i in range(bays_x):
                    for j in range(bays_y):
                        # Proyom o'lchamlari
                        bay_x = sx  # X yonalish
                        bay_y = sy  # Y yonalish
                        
                        # PK uzunligi — Y yonalishda yotadi
                        # Balkaga 130mm kirib turadi
                        pk_uzun = bay_y - mm(0) / metr(1)  # sof oraliq
                        
                        # X yonalishda nechta PK sig'adi
                        sof_x = bay_x  # balka oraligi
                        pk_soni = int(sof_x / pk_eni)
                        qoldiq = sof_x - pk_soni * pk_eni
                        
                        # Har bir PK ni joylashtirish
                        for n in range(pk_soni):
                            x1 = metr(x0 + i * sx) + slab_offset + metr(n * pk_eni)
                            x2 = x1 + metr(pk_eni)
                            # Y: balkaga 130mm kirib turadi
                            y1 = metr(x0 + j * sy + 0) + slab_offset - metr(tayanchiq)
                            y2 = metr(x0 + (j+1) * sy + 0) - slab_offset + metr(tayanchiq)
                            
                            # Haqiqiy koordinatalar
                            px1 = metr(x0 + i*sx) + slab_offset + metr(n * pk_eni)
                            px2 = px1 + metr(pk_eni)
                            py1 = metr(y0 + j*sy) + slab_offset - metr(tayanchiq)
                            py2 = metr(y0 + (j+1)*sy) - slab_offset + metr(tayanchiq)
                            
                            if px2 > px1 and py2 > py1:
                                plita_panel_yarat(px1, py1, px2, py2, z_tepa, f_type, level)
                        
                        # Qoldiq joy uchun kichik PK
                        if qoldiq > 0.1:
                            px1 = metr(x0 + i*sx) + slab_offset + metr(pk_soni * pk_eni)
                            px2 = metr(x0 + (i+1)*sx) - slab_offset
                            py1 = metr(y0 + j*sy) + slab_offset - metr(tayanchiq)
                            py2 = metr(y0 + (j+1)*sy) - slab_offset + metr(tayanchiq)
                            if px2 > px1 and py2 > py1:
                                plita_panel_yarat(px1, py1, px2, py2, z_tepa, f_type, level)
            else:
                # ===== MONOLIT PLITA =====
                for i in range(bays_x):
                    for j in range(bays_y):
                        x1 = metr(x0+i*sx) + slab_offset
                        y1 = metr(y0+j*sy) + slab_offset
                        x2 = metr(x0+(i+1)*sx) - slab_offset
                        y2 = metr(y0+(j+1)*sy) - slab_offset
                        if x2 > x1 and y2 > y1:
                            plita_panel_yarat(x1, y1, x2, y2, z_tepa, f_type, level)

    t.Commit()
    if progress_cb: progress_cb(100, "Bino qurildi!")
    return True

# ===== SPETSIFIKATSIYA =====
def hajm_yigindi(kategoriya):
    col = FilteredElementCollector(doc).OfCategory(kategoriya).WhereElementIsNotElementType()
    soni = 0; hajm = 0.0
    for el in col:
        p = el.get_Parameter(BuiltInParameter.HOST_VOLUME_COMPUTED)
        if p:
            v = p.AsDouble()
            if v > 0: hajm += v; soni += 1
    return soni, kub_metr(hajm)

def spets_chiqar(loyiha="", muhandis=""):
    k_soni, k_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralColumns)
    b_soni, b_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralFraming)
    p_soni, p_hajm = hajm_yigindi(BuiltInCategory.OST_Floors)
    w_soni, w_hajm = hajm_yigindi(BuiltInCategory.OST_Walls)
    f_soni, f_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralFoundation)
    jami = k_hajm + b_hajm + p_hajm + w_hajm + f_hajm
    if jami == 0: forms.alert("Loyihada elementlar topilmadi!"); return
    out = output.get_output()
    out.close_others()
    out.set_title("Revit AI - Spetsifikatsiya")
    if loyiha: out.print_md("## Loyiha: " + loyiha)
    if muhandis: out.print_md("## Muhandis: " + muhandis)
    out.print_md("## Sana: " + datetime.now().strftime("%d.%m.%Y"))
    out.print_md("---")
    out.print_md("# BETON SPETSIFIKATSIYASI")
    sarlavha = ["No", "Element", "Soni", "Hajm (m3)", "Ulush (%)"]
    qatorlar = []; n = 1
    if f_soni > 0:
        qatorlar.append([str(n), "Fundament podushka", str(f_soni)+" ta", str(round(f_hajm,3)), str(round(f_hajm/jami*100,1))+"%"]); n+=1
    if w_soni > 0:
        qatorlar.append([str(n), "Fundament lenta", str(w_soni)+" ta", str(round(w_hajm,3)), str(round(w_hajm/jami*100,1))+"%"]); n+=1
    if k_soni > 0:
        qatorlar.append([str(n), "Kolonnalar", str(k_soni)+" ta", str(round(k_hajm,3)), str(round(k_hajm/jami*100,1))+"%"]); n+=1
    if b_soni > 0:
        qatorlar.append([str(n), "Balkalar (rigellar)", str(b_soni)+" ta", str(round(b_hajm,3)), str(round(b_hajm/jami*100,1))+"%"]); n+=1
    if p_soni > 0:
        qatorlar.append([str(n), "Perekritie", str(p_soni)+" ta", str(round(p_hajm,3)), str(round(p_hajm/jami*100,1))+"%"]); n+=1
    qatorlar.append(["", "JAMI BETON", "", str(round(jami,3)), "100%"])
    out.print_table(qatorlar, title="Beton elementlari", columns=sarlavha)
    out.print_md("---")
    out.print_md("## JAMI BETON: " + str(round(jami,3)) + " m3")

def excel_saqlash(loyiha="", muhandis=""):
    k_soni, k_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralColumns)
    b_soni, b_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralFraming)
    p_soni, p_hajm = hajm_yigindi(BuiltInCategory.OST_Floors)
    w_soni, w_hajm = hajm_yigindi(BuiltInCategory.OST_Walls)
    f_soni, f_hajm = hajm_yigindi(BuiltInCategory.OST_StructuralFoundation)
    jami = k_hajm + b_hajm + p_hajm + w_hajm + f_hajm
    if jami == 0: forms.alert("Loyihada elementlar topilmadi!"); return
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    sana = datetime.now().strftime("%Y%m%d_%H%M%S")
    fayl = os.path.join(desktop, "Spetsifikatsiya_" + sana + ".csv")
    qatorlar = ["BETON SPETSIFIKATSIYASI", "Loyiha:," + loyiha, "Muhandis:," + muhandis, "Sana:," + datetime.now().strftime("%d.%m.%Y"), "", "No,Element,Soni,Hajm (m3),Ulush (%)"]
    n = 1
    if f_soni > 0:
        qatorlar.append(str(n)+",Fundament podushka,"+str(f_soni)+" ta,"+str(round(f_hajm,3))+","+str(round(f_hajm/jami*100,1))+"%"); n+=1
    if w_soni > 0:
        qatorlar.append(str(n)+",Fundament lenta,"+str(w_soni)+" ta,"+str(round(w_hajm,3))+","+str(round(w_hajm/jami*100,1))+"%"); n+=1
    if k_soni > 0:
        qatorlar.append(str(n)+",Kolonnalar,"+str(k_soni)+" ta,"+str(round(k_hajm,3))+","+str(round(k_hajm/jami*100,1))+"%"); n+=1
    if b_soni > 0:
        qatorlar.append(str(n)+",Balkalar,"+str(b_soni)+" ta,"+str(round(b_hajm,3))+","+str(round(b_hajm/jami*100,1))+"%"); n+=1
    if p_soni > 0:
        qatorlar.append(str(n)+",Perekritie,"+str(p_soni)+" ta,"+str(round(p_hajm,3))+","+str(round(p_hajm/jami*100,1))+"%"); n+=1
    qatorlar.append(",JAMI BETON,,"+str(round(jami,3))+",100%")
    with open(fayl, "w") as f:
        f.write("\n".join(qatorlar))
    forms.alert("Excel (CSV) saqlandi:\n" + fayl, title="Revit AI")

# ===== WPF OYNA =====
class RevitAIForm(Window):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), "RevitAI.xaml")
        wpf.LoadComponent(self, xaml_path)
        self.fund_turi.SelectionChanged += self.fund_turi_SelectionChanged
    def fund_turi_SelectionChanged(self, sender, e):
        try:
            idx = sender.SelectedIndex
            self.lenta_params.Visibility = Visibility.Visible if idx == 0 else Visibility.Collapsed
            self.monolit_params.Visibility = Visibility.Collapsed if idx == 0 else Visibility.Visible
        except: pass
    def _f(self, name, default=0):
        try: return float(getattr(self, name).Text)
        except: return default
    def _t(self, name, default=""):
        try: return getattr(self, name).Text.strip()
        except: return default
    def _b(self, name):
        try: return getattr(self, name).IsChecked == True
        except: return False
    def _progress(self, value, text):
        try:
            self.progress_bar.Value = value
            self.status_txt.Text = text
            self.UpdateLayout()
        except: pass
    def btn_qurish_Click(self, sender, e):
        fund_idx = self.fund_turi.SelectedIndex
        plita_idx = self.plita_turi.SelectedIndex
        p = {
            "eni": self._f("bino_eni", 12), "uzunligi": self._f("bino_uzunligi", 18),
            "qadam": self._f("qadam", 6), "qavatlar": int(self._f("qavatlar", 2)),
            "qavat_h": self._f("qavat_balandligi", 3),
            "k_olcham": self._t("kolonna_olcham", "400x400"),
            "b_olcham": self._t("rigel_olcham", "400x600"),
            "plita_turi": "pk" if plita_idx == 1 else "monolit",
            "plita_q": self._f("plita_qalinligi", 200),
            "x0": self._f("x_boshlash", 0), "y0": self._f("y_boshlash", 0),
            "fund_kerak": self._b("cb_fundament"), "osi_kerak": self._b("cb_osi"),
            "plita_kerak": self._b("cb_plita"),
            "fund_turi": "lenta" if fund_idx == 0 else "monolit",
            "pod_eni": self._f("podushka_eni", 1000), "pod_qalin": self._f("podushka_qalinligi", 400),
            "lenta_eni": self._f("lenta_eni", 400), "lenta_baland": self._f("lenta_balandligi", 600),
            "monolit_qalin": self._f("monolit_qalinligi", 400), "monolit_chiqish": self._f("monolit_chiqish", 500),
        }
        self._progress(5, "Boshlanmoqda...")
        natija = bino_qur(p, self._progress)
        if natija: self._progress(100, "Bino muvaffaqiyatli qurildi!")
    def btn_spets_Click(self, sender, e):
        spets_chiqar(self._t("loyiha_nomi"), self._t("muhandis_nomi"))
    def btn_excel_Click(self, sender, e):
        excel_saqlash(self._t("loyiha_nomi"), self._t("muhandis_nomi"))
    def btn_undo_Click(self, sender, e):
        try:
            doc.Undo()
            self._progress(0, "Undo bajarildi!")
        except: forms.alert("Undo bajarilmadi!")

form = RevitAIForm()
form.ShowDialog()