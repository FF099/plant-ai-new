import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from openai import OpenAI

from .models import Admin, PlantCategory, Plant, Faq, SearchSummary, record_search
from .forms import PlantForm, PlantCategoryForm, FaqForm, AdminUserForm, AdminLoginForm

# เรียกใช้ OpenAI API Client
# ดึงค่า OPENAI_API_KEY จาก settings.py (ถ้าไม่มีให้ใช้ค่าว่าง '' แทน เพื่อไม่ให้ error ตอน import)
client = OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))


# ─────────────────────────────────────────────
#  1. Map คีย์เวิร์ดภาษาไทย -> Value จริงใน Database ('low', 'medium', 'high')
#     ใช้ตรวจจับว่าผู้ใช้พิมพ์คำที่สื่อถึงระดับแสง/น้ำ/ความชื้นแบบไหนในข้อความแชท
# ─────────────────────────────────────────────
LIGHT_MAP = {
    # ถ้าข้อความผู้ใช้มีคำใดคำหนึ่งในลิสต์นี้ ให้ตีความว่าหมายถึงระดับแสง 'low'
    'low': ["แสงน้อย", "ในร่ม", "ในบ้าน", "ห้องนอน", "โต๊ะทำงาน", "ไม่ชอบแดด", "ไม่โดนแดด", "แสงรำไรน้อย", "ร่มรื่น", "มุมมืด"],
    'medium': ["แสงปานกลาง", "รำไร", "แสงรำไร", "แดดเช้า", "แดดอ่อน", "โต๊ะริมหน้าต่าง", "แดดรำไร", "แดดไม่แรง"],
    'high': ["แสงมาก", "แสงแดดจ้า", "แดดจัด", "กลางแจ้ง", "แดดแรง", "แดดตลอดวัน", "ชอบแดด", "ทนแดด", "แดด 100", "ระเบียง"]
}

WATER_MAP = {
    'low': ["น้ำน้อย", "รดน้ำน้อย", "ทนแล้ง", "ไม่ชอบน้ำ", "อาทิตย์ละครั้ง", "สัปดาห์ละครั้ง", "นานๆ รด", "ไม่ค่อยรดน้ำ", "ลืมรดน้ำ"],
    'medium': ["น้ำปานกลาง", "รดน้ำปานกลาง", "วันเว้นวัน", "2-3 วัน", "ชุ่มชื้นพอดี"],
    'high': ["น้ำมาก", "รดน้ำมาก", "ชอบน้ำ", "รดน้ำทุกวัน", "ชอบแช่น้ำ", "น้ำชุ่ม", "ชอบความชุ่มฉ่ำ"]
}

HUMIDITY_MAP = {
    'low': ["ความชื้นต่ำ", "อากาศแห้ง", "ห้องแอร์", "แห้งๆ"],
    'medium': ["ความชื้นปานกลาง"],
    'high': ["ความชื้นสูง", "ชอบชื้น", "ชื้นมาก", "ห้องน้ำ", "โรงเรือน", "ละอองน้ำ"]
}

# Map คำพ้อง/คำย่อของแต่ละหมวดหมู่พืช -> ใช้จับคู่กับคำในข้อความผู้ใช้
# key คือชื่อหมวดหมู่แบบเต็ม (ต้องตรงกับ category_name ใน DB), value คือลิสต์คำที่ใช้แทนกันได้
CATEGORY_SYNONYMS = {
    "ไม้คลุมดิน": ["คลุมดิน"],
    "ไม้ล้มลุก": ["ล้มลุก"],
    "ไม้พุ่ม": ["พุ่ม"],
    "ไม้ยืนต้น": ["ยืนต้น", "ต้นไม้ใหญ่"],
    "ไม้เลื้อย": ["เลื้อย", "ไม้เถา", "เถา"],
    "ไม้ประดับอื่น": ["ไม้ประดับ", "ประดับ", "อื่นๆ", "อื่น ๆ", "ทั่วไป"],
}


# ─────────────────────────────────────────────
#  1.1 PLANT_SYNONYMS — คำพ้อง/ชื่อเรียกอื่น/ชื่อย่อ/สะกดผิด/ชื่ออังกฤษของพืชแต่ละต้น
#      key   = ชื่อพืชตรงตัวใน DB (plant_name)
#      value = list คำที่ผู้ใช้อาจพิมพ์แทน (อย่างน้อย 1 ชื่อเป็นภาษาอังกฤษ/วิทยาศาสตร์)
#
#      ⚠️ หมายเหตุ: ชื่ออังกฤษ/วิทยาศาสตร์ของพืชไทยพื้นบ้านบางต้น (เช่น กลุ่ม
#      "ว่านเสน่ห์จันทร์", "พลูฉลุ/พลูฉีก/พลูสนิม", "ออมเงิน/ออมทอง") ไม่มีมาตรฐานตายตัว
#      ใส่ชื่อที่ใกล้เคียงที่สุดเท่าที่หาข้อมูลได้ ควรตรวจสอบซ้ำก่อนใช้งานจริง
# ─────────────────────────────────────────────
PLANT_SYNONYMS = {
    "เล็บครุฑใบกุหลาบ": ["เล็บครุฑกุหลาบ", "อาราเลียใบกุหลาบ", "ming aralia", "aralia"],
    "เล็บครุฑใบเฟิร์น": ["เล็บครุฑเฟิร์น", "เล็บครุฑใบชวน", "fern leaf aralia", "fern aralia"],
    "เล็บครุฑบริพัตร": ["เล็บครุฑบริพันธ์", "บริพัตร", "balfour aralia"],
    "เล็บครุฑฝอย": ["เล็บครุฑใบฝอย", "thread leaf aralia", "parsley aralia"],
    "บอนสี": ["บอน", "บอนใบสี", "caladium", "heart of jesus"],
    "ออมเงินกำมะหยี่": ["ต้นออมเงินกำมะหยี่", "กำมะหยี่ออมเงิน", "satin pothos", "silver pothos"],
    "ออมทอง": ["ต้นออมทอง", "golden satin pothos"],
    "ว่านเสน่ห์จันทร์แดง": ["เสน่ห์จันทร์แดง", "ว่านเสน่ห์จันทน์แดง", "aglaonema red", "chinese evergreen แดง"],
    "ว่านเสน่ห์จันทร์เขียว": ["เสน่ห์จันทร์เขียว", "ว่านเสน่ห์จันทน์เขียว", "aglaonema green", "chinese evergreen เขียว"],
    "ว่านเสน่ห์จันทร์ขาว": ["เสน่ห์จันทร์ขาว", "ว่านเสน่ห์จันทน์ขาว", "aglaonema white", "chinese evergreen ขาว"],
    "พลูฉลุ": ["พลูฉลุลาย", "monstera adansonii", "swiss cheese vine"],
    "พลูฉีก": ["พลูใบฉีก", "split leaf philodendron"],
    "พลูสนิม": ["พลูใบสนิม", "rusty pothos"],
    "ฟิโลเดนดรอน": ["ฟิโล", "philodendron"],
    "ลิ้นมังกร": ["ลิ้นมังกรใบ", "snake plant tongue", "gasteria"],
    "เดหลี": ["เดหลี่", "ดีหลี", "peace lily", "spathiphyllum"],
    "เขียวหมื่นปี": ["ต้นเขียวหมื่นปี", "chinese evergreen", "aglaonema"],
    "สาวน้อยประแป้ง": ["สาวน้อยแป้งประ", "dumb cane", "dieffenbachia"],
    "หมากผู้หมากเมีย": ["หมากผู้-หมากเมีย", "rhoeo", "moses in the cradle", "tradescantia spathacea"],
    "วาสนา": ["ต้นวาสนา", "dracaena", "lucky plant"],
    "หมากแดง": ["ปาล์มหมากแดง", "red sealing wax palm", "lipstick palm"],
    "เฟิร์นหางปลา": ["fishtail fern", "fish tail fern"],
    "เฟิร์นใบบะขาม (เฟิร์นใบมะขาม)": ["เฟิร์นใบบะขาม", "เฟิร์นใบมะขาม", "เฟิร์นมะขาม", "tamarind leaf fern"],
    "คล้าม้าลาย": ["ม้าลาย", "zebra plant", "calathea zebrina"],
    "กาเหว่าลาย": ["กาเหว่า", "croton variegated", "codiaeum กาเหว่า"],
    "ว่านเศรษฐีขอดทรัพย์": ["เศรษฐีขอดทรัพย์", "money plant ขอดทรัพย์"],
    "ว่านเศรษฐีเรือนกลาง": ["เศรษฐีเรือนกลาง", "money plant เรือนกลาง"],
    "ว่านเศรษฐีเรือนนอก": ["เศรษฐีเรือนนอก", "money plant เรือนนอก"],
    "ว่านเศรษฐีเรือนใน": ["เศรษฐีเรือนใน", "money plant เรือนใน"],
    "กวนอิม": ["ต้นกวนอิม", "guanyin plant", "homalomena"],
    "หวายเขียว": ["green rattan", "หวายลาย"],
    "ไผ่ฟิลิปปินส์": ["ไผ่ฟิลิปปิน", "philippine bamboo", "golden bamboo"],
    "แอฟริกัน ไวโอเล็ต": ["แอฟริกันไวโอเล็ต", "ไวโอเล็ต", "african violet", "saintpaulia"],
    "พรมญี่ปุ่น": ["หญ้าพรมญี่ปุ่น", "japanese carpet grass", "zoysia"],
    "เฟิร์นนาคราช": ["นาคราช", "king fern", "blue star fern"],
    "กุหลาบหิน": ["kalanchoe", "stone rose", "flaming katy"],
    "ก้ามปูหลุด": ["ก้ามปู", "rhipsalis", "mistletoe cactus"],
    "แคัคตัส (แคคตัส)": ["แคคตัส", "แคกตัส", "แคกทัส", "กระบองเพชร", "cactus"],
    "สัปปะรดสี (สับปะรดสี)": ["สัปปะรดสี", "สับปะรดสี", "สัปรดสี", "bromeliad"],
    "เฟิร์นข้าหลวง": ["ข้าหลวง", "bird's nest fern", "asplenium"],
    "เฟิร์นก้านดำ": ["ก้านดำ", "maidenhair fern", "adiantum"],
    "โกสน": ["ต้นโกสน", "croton", "codiaeum"],
    "ไทรย้อยใบแหลม": ["ไทรย้อย", "weeping fig", "ficus benjamina"],
    "เกล็ดมังกร": ["dragon scale", "alocasia baginda"],
    "ซ้อนเงินซ้อนทอง": ["ซ้อนเงินซ้อนคำ", "aglaonema pictum"],
    "เงินไหลมา": ["money coming plant", "aglaonema commutatum"],
    "ปาล์มไผ่": ["bamboo palm", "chamaedorea"],
    "หน้าวัว": ["anthurium", "flamingo flower"],
    "บีโกเนีย": ["begonia"],
    "ริบบิ้นชาลี": ["ริบบิ้น", "spider plant", "chlorophytum"],
    "คล้าขุนแผน": ["ขุนแผน", "calathea ornata", "pinstripe calathea"],
    "เฟิร์นบอสตัน": ["boston fern", "nephrolepis"],
    "ซานาดู": ["xanadu", "philodendron xanadu"],
    "พลูด่าง": ["pothos", "devil's ivy", "epipremnum aureum"],
    "กวักมรกต": ["มรกต", "zz plant", "zamioculcas"],
    "ไทรใบสัก": ["fiddle leaf fig", "ficus lyrata"],
    "ยางอินเดีย": ["rubber plant", "ficus elastica"],
    "มอนสเตอร่า": ["ม่อนสเตอร่า", "monstera", "monstera deliciosa", "swiss cheese plant"],
    "เปปเปอร์โรเมีย": ["เปปเปอโรเมีย", "peperomia"],
    "เฟิร์นเงิน": ["silver fern", "pteris"],
    "จั๋ง": ["จัง", "rhapis", "lady palm"],
    "หมากเหลือง": ["golden cane palm", "areca palm", "dypsis lutescens"],
    "พวงไข่มุก": ["ไข่มุก", "string of pearls", "senecio rowleyanus"],
    "ว่านหางจระเข้": ["หางจระเข้", "ว่านหางจรเข้", "aloe vera"],
    "บันไดเศรษฐี": ["money ladder plant", "pedilanthus"],
    "บัวดอย": ["ดอกบัวดอย", "rhododendron ดอย", "vireya"],
    "ทิลแลนเซีย": ["ทิลแลนด์เซีย", "tillandsia", "air plant"],
    "โฮย่า": ["hoya", "wax plant"],
    "ปริกหางกระรอก": ["หางกระรอก", "squirrel tail orchid", "dendrobium"],
    "เข็มริมแดง": ["red edge ixora", "ixora"],
}


# ─────────────────────────────────────────────
#  1.2 รองรับกรณี "พิมพ์สลับภาษา" (ลืมสลับคีย์บอร์ด EN/TH)
#      ผู้ใช้ตั้งใจพิมพ์ไทย แต่คีย์บอร์ดอยู่โหมดอังกฤษ -> ได้ตัวอักษรละตินที่ไม่มีความหมาย
#      เช่น "โกสน" (กดตำแหน่งปุ่มจริง) -> ออกมาเป็น "Fdlo" บนคีย์บอร์ด EN
#      เรา map ตำแหน่งปุ่มกลับเป็นภาษาไทยตามผัง Kedmanee (ผังมาตรฐานของไทย)
# ─────────────────────────────────────────────
KEDMANEE_UNSHIFTED = {
    'q': 'ๆ', 'w': 'ไ', 'e': 'ำ', 'r': 'พ', 't': 'ะ', 'y': 'ั', 'u': 'ี', 'i': 'ร', 'o': 'น', 'p': 'ย',
    '[': 'บ', ']': 'ล', '\\': 'ฃ',
    'a': 'ฟ', 's': 'ห', 'd': 'ก', 'f': 'ด', 'g': 'เ', 'h': '้', 'j': '่', 'k': 'า', 'l': 'ส', ';': 'ว', "'": 'ง',
    'z': 'ผ', 'x': 'ป', 'c': 'แ', 'v': 'อ', 'b': 'ิ', 'n': 'ื', 'm': 'ท', ',': 'ม', '.': 'ใ', '/': 'ฝ',
}
KEDMANEE_SHIFTED = {
    'Q': '๐', 'W': '"', 'E': 'ฎ', 'R': 'ฑ', 'T': 'ธ', 'Y': 'ํ', 'U': '๊', 'I': 'ณ', 'O': 'ฯ', 'P': 'ญ',
    '{': 'ฐ', '}': ',',
    'A': 'ฤ', 'S': 'ฆ', 'D': 'ฏ', 'F': 'โ', 'G': 'ฌ', 'H': '็', 'J': '๋', 'K': 'ษ', 'L': 'ศ', ':': 'ซ', '"': '.',
    'Z': '(', 'X': ')', 'C': 'ฉ', 'V': 'ฮ', 'B': 'ฺ', 'N': '์', 'M': '?', '<': 'ฒ', '>': 'ฬ', '?': 'ฦ',
}
_KEDMANEE_MAP = {**KEDMANEE_UNSHIFTED, **KEDMANEE_SHIFTED}


def fix_kedmanee_typo(text: str) -> str:
    """
    แปลงข้อความที่พิมพ์ผิดภาษา (ตั้งใจพิมพ์ไทยแต่ลืมสลับเป็นคีย์บอร์ด EN)
    กลับเป็นข้อความไทยที่ตั้งใจพิมพ์จริง โดย map ตามตำแหน่งปุ่ม Kedmanee
    เช่น fix_kedmanee_typo("Fdlo") -> "โกสน"
    ตัวอักษรที่ไม่อยู่ใน mapping (เช่น เป็นภาษาไทยอยู่แล้ว ตัวเลข ช่องว่าง) จะคงค่าเดิม
    """
    return ''.join(_KEDMANEE_MAP.get(ch, ch) for ch in text)


def _clean(text: str) -> str:
    """ลบช่องว่าง/ไม้ยมก + lower-case (ใช้เทียบคำแบบไม่สนตัวพิมพ์เล็ก/ใหญ่ ไม่สนช่องว่าง)"""
    return re.sub(r'[\sๆ]', '', text.lower())


def build_search_variants(user_input: str):
    """
    สร้างข้อความหลายเวอร์ชันไว้ใช้ค้นหา เรียงตามลำดับความสำคัญ:
      1. ข้อความต้นฉบับ (ปกติ)
      2. ข้อความที่ 'แก้พิมพ์ผิดภาษา' แบบคีย์บอร์ด Kedmanee
         (จะเพิ่มเข้ามาเฉพาะเมื่อแปลงแล้วได้ผลลัพธ์ต่างจากต้นฉบับ)
    คืนค่าเป็น list ของ (lower_text, clean_text)
    """
    variants = []

    original_lower = user_input.lower()
    variants.append((original_lower, _clean(original_lower)))

    fixed = fix_kedmanee_typo(user_input)
    if fixed != user_input:
        fixed_lower = fixed.lower()
        variants.append((fixed_lower, _clean(fixed_lower)))

    return variants


# reverse-lookup: alias(clean) -> canonical plant_name
# สร้างครั้งเดียวตอน import, เรียงยาว->สั้น กัน alias สั้นแย่ง match ก่อน alias ที่เจาะจงกว่า
_PLANT_ALIAS_LOOKUP = []
for _canonical_name, _aliases in PLANT_SYNONYMS.items():
    _all_terms = set(_aliases) | {_canonical_name}
    for _term in _all_terms:
        _PLANT_ALIAS_LOOKUP.append((_clean(_term), _canonical_name))
_PLANT_ALIAS_LOOKUP.sort(key=lambda pair: len(pair[0]), reverse=True)


def match_plant_names(user_input: str):
    """
    ตรวจว่าข้อความผู้ใช้มีชื่อพืช/คำพ้อง/ชื่ออังกฤษของพืชตัวไหนบ้าง
    รองรับทั้งข้อความปกติ และข้อความที่พิมพ์ผิดภาษา (คีย์บอร์ด EN/TH สลับกัน)
    คืนค่าเป็น set ของชื่อพืชจริง (canonical, ตรงกับ plant_name ใน DB)
    """
    matched = set()
    for _lower, clean_text in build_search_variants(user_input):
        for alias_clean, canonical_name in _PLANT_ALIAS_LOOKUP:
            if len(alias_clean) >= 2 and alias_clean in clean_text:
                matched.add(canonical_name)
        if matched:
            # เจอจาก variant นี้แล้ว ไม่ต้องลอง variant ถัดไป (variant แรกมาก่อนเสมอ)
            break
    return matched


# ─────────────────────────────────────────────
#  2. Custom Decorator สำหรับตรวจสอบการเข้าสู่ระบบผู้ดูแลระบบ
#     ใช้ครอบ (decorate) view ที่ต้องการให้เข้าถึงได้เฉพาะ admin ที่ login แล้วเท่านั้น
# ─────────────────────────────────────────────
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        # ตรวจสอบว่ามี key 'admin_id' อยู่ใน session หรือไม่ (ถูกตั้งค่าตอน login สำเร็จใน login_view)
        if 'admin_id' not in request.session:
            # ถ้ายังไม่ login ให้ redirect ไปหน้า login ทันที แทนที่จะเรียก view จริง
            return redirect('login')
        # ถ้า login แล้ว ให้เรียก view function ตัวจริงทำงานต่อตามปกติ
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
#  3. RAG — ค้นหาข้อมูลพืชจาก DB ตามคำถามผู้ใช้
#     (RAG = Retrieval-Augmented Generation คือดึงข้อมูลจริงจาก DB มาป้อนให้ AI ใช้ตอบ
#      แทนที่จะให้ AI ตอบจากความรู้ที่มันมีเอง เพื่อป้องกันการตอบมั่ว/หลอน (hallucination))
#
#      ปรับปรุงจากเดิม: เพิ่มขั้นตอน D0 ตรวจชื่อพืชเจาะจงก่อน (ผ่าน PLANT_SYNONYMS)
#      และทุกขั้นตอน A-D ตรวจกับทั้งข้อความต้นฉบับ + ข้อความที่แก้พิมพ์ผิดภาษาแล้ว
# ─────────────────────────────────────────────
def get_plant_context(user_input):
    # ดึงพืชทั้งหมดพร้อม join ตาราง category ไว้ล่วงหน้า (select_related) เพื่อลดจำนวน query ตอน loop
    plants = Plant.objects.select_related('category').all()

    # สร้างข้อความหลายเวอร์ชันไว้เทียบ (ต้นฉบับ + เวอร์ชันแก้พิมพ์ผิดภาษาคีย์บอร์ด ถ้ามี)
    variants = build_search_variants(user_input)  # [(lower_text, clean_text), ...]

    # ── D0: ตรวจหาชื่อพืชเจาะจงก่อนเป็นอันดับแรก (สำคัญสุด) ──
    matched_plant_names = match_plant_names(user_input)
    if matched_plant_names:
        target_plants = plants.filter(plant_name__in=matched_plant_names).distinct()
        if target_plants.exists():
            context = "รายการต้นไม้ที่ค้นพบในระบบ (ค้นหาแบบระบุชื่อพืชโดยตรง):\n"
            for p in target_plants:
                context += f"""
- ชื่อ: {p.plant_name}
  หมวดหมู่: {p.category.category_name}
  แสง: {p.get_light_display()} | น้ำ: {p.get_water_display()} | ความชื้น: {p.get_humidity_display()}
  รายละเอียด: {p.description or "-"}
-------------------
"""
            return context
        # ถ้า filter ไม่เจอ (เช่นข้อมูลถูกลบไปแล้ว) ให้ตกไปทำ logic เดิมต่อด้านล่าง

    attr_query = Q()  # ตัวเก็บเงื่อนไข query ที่จะค่อยๆ AND (&) เพิ่มเข้าไปตามคุณสมบัติที่ตรวจเจอ
    has_attr = False  # flag บอกว่ามีการตรวจเจอคุณสมบัติ (แสง/น้ำ/ความชื้น/หมวดหมู่) อย่างน้อย 1 อย่างหรือไม่

    # ตัวแปรเก็บค่าที่ตรวจเจอ เพื่อเอาไปบันทึกลง SearchLog/SearchSummary ภายหลัง
    selected_light = None
    selected_water = None
    selected_humidity = None
    selected_category_obj = None

    def any_variant_has(keywords):
        """เช็คว่ามี keyword ใดปรากฏใน variant ไหนก็ได้ (ต้นฉบับ หรือแก้พิมพ์ผิดภาษาแล้ว)"""
        for lower_text, _clean_text in variants:
            if any(kw in lower_text for kw in keywords):
                return True
        return False

    # A. ตรวจหาแสง — วนดูทีละระดับ (low/medium/high) ว่ามีคำใน keywords ปรากฏในข้อความผู้ใช้หรือไม่
    for db_val, keywords in LIGHT_MAP.items():
        if any_variant_has(keywords):
            attr_query &= Q(light=db_val)  # เพิ่มเงื่อนไข filter(light=db_val) เข้าไปใน query
            selected_light = db_val
            has_attr = True
            break  # เจอแล้วหยุดค้นระดับอื่นทันที (ตรวจเจอได้แค่ระดับเดียวต่อการค้นหาหนึ่งครั้ง)

    # B. ตรวจหาน้ำ (ตรรกะเดียวกับ A แต่ใช้ WATER_MAP)
    for db_val, keywords in WATER_MAP.items():
        if any_variant_has(keywords):
            attr_query &= Q(water=db_val)
            selected_water = db_val
            has_attr = True
            break

    # C. ตรวจหาความชื้น (ตรรกะเดียวกับ A แต่ใช้ HUMIDITY_MAP)
    for db_val, keywords in HUMIDITY_MAP.items():
        if any_variant_has(keywords):
            attr_query &= Q(humidity=db_val)
            selected_humidity = db_val
            has_attr = True
            break

    # D. ตรวจหาหมวดหมู่ — ต่างจาก A-C ตรงที่ต้องดึงหมวดหมู่จริงจาก DB มาเทียบ
    #    (เพราะชื่อหมวดหมู่ผูกกับข้อมูลจริงในตาราง ไม่ได้ fix ค่าตายตัวเหมือน light/water/humidity)
    matched_category_ids = set()  # เก็บ category_id ที่ตรงเงื่อนไข (อาจตรงได้มากกว่า 1 หมวด)
    db_categories = PlantCategory.objects.all()
    for cat in db_categories:
        if not cat.category_name:
            continue  # ข้ามหมวดหมู่ที่ไม่มีชื่อ (กันข้อมูลผิดปกติ)
        # ลบช่องว่าง/ไม้ยมกออกจากชื่อหมวดหมู่ เพื่อเทียบกับ clean_text ได้ตรงกัน
        cat_name_clean = _clean(cat.category_name)

        for lower_text, clean_text in variants:
            # เทียบตรงๆ: ถ้าชื่อหมวดหมู่ (ที่ตัดช่องว่างแล้ว) ยาวอย่างน้อย 2 ตัวอักษร และปรากฏอยู่ในข้อความผู้ใช้
            if len(cat_name_clean) >= 2 and cat_name_clean in clean_text:
                matched_category_ids.add(cat.category_id)
                selected_category_obj = cat

            # เทียบผ่านคำพ้อง: ถ้าชื่อหมวดหมู่มีคำ key ใน CATEGORY_SYNONYMS ปรากฏอยู่
            # และข้อความผู้ใช้มีคำพ้อง (syn_words) คำใดคำหนึ่งของ key นั้น ก็ถือว่าตรงกันด้วย
            for syn_key, syn_words in CATEGORY_SYNONYMS.items():
                if syn_key in cat_name_clean and any(sw in lower_text for sw in syn_words):
                    matched_category_ids.add(cat.category_id)
                    selected_category_obj = cat

    if matched_category_ids:
        # ถ้าเจอหมวดหมู่ที่ตรง ให้เพิ่มเงื่อนไข category_id อยู่ใน list ที่เจอ (อาจมากกว่า 1 หมวด)
        attr_query &= Q(category_id__in=list(matched_category_ids))
        has_attr = True

    # E. บันทึก SearchLog และ Query ฐานข้อมูล
    if has_attr:
        # ถ้าตรวจเจอคุณสมบัติอย่างน้อย 1 อย่าง ให้บันทึกลง log/summary (และอาจ auto-gen FAQ)
        try:
            record_search(
                filter_light=selected_light,
                filter_water=selected_water,
                filter_humidity=selected_humidity,
                filter_category=selected_category_obj
            )
        except Exception as e:
            # ถ้าการบันทึก log ล้มเหลว ไม่ให้กระทบการค้นหาพืชหลัก แค่ print แจ้ง error ไว้
            print(f"Record search log error: {e}")

        # กรองพืชด้วยเงื่อนไขทั้งหมดที่สะสมไว้ + distinct() กันข้อมูลซ้ำจากการ join
        target_plants = plants.filter(attr_query).distinct()
    else:
        # ถ้าไม่พบคุณสมบัติที่กำหนดไว้
        # ให้ดึงข้อมูลพืชจากฐานข้อมูลมาให้ LLM พิจารณาเอง
        # โดย LLM จะเลือกจากข้อมูล RAG ที่ได้รับเท่านั้น
        target_plants = plants.all()

    if not target_plants.exists():
        # ถ้าไม่พบพืชที่ตรงเงื่อนไขเลย ส่งข้อความแจ้งกลับไปเป็น context (ให้ AI เอาไปใช้ตอบ)
        return "ไม่พบข้อมูลต้นไม้ที่ตรงตามเงื่อนไขที่ระบุในฐานข้อมูล"

    # สร้างข้อความส่งให้ GPT (ใช้ get_FOO_display() เพื่อแปลง 'low' เป็น 'แสงน้อย' อัตโนมัติ)
    # ประกอบรายละเอียดพืชแต่ละต้นที่เจอ เป็น string เดียว เพื่อส่งเข้าไปเป็น context ให้ LLM ใช้อ้างอิงตอบ
    context = "รายการต้นไม้ที่ค้นพบในระบบ:\n"
    for p in target_plants:
        context += f"""
- ชื่อ: {p.plant_name}
  หมวดหมู่: {p.category.category_name}
  แสง: {p.get_light_display()} | น้ำ: {p.get_water_display()} | ความชื้น: {p.get_humidity_display()}
  รายละเอียด: {p.description or "-"}
-------------------
"""
    return context


# ─────────────────────────────────────────────
#  4. Public Views
#     views ที่ผู้ใช้ทั่วไป (ไม่ต้อง login) เข้าถึงได้
# ─────────────────────────────────────────────
def index(request):
    # หน้าแรก: แสดงรายการพืชทั้งหมด พร้อมรองรับการค้นหา/filter ผ่าน query string (GET parameters)
    plants = Plant.objects.all()
    categories = PlantCategory.objects.all()  # ใช้แสดงเป็นตัวเลือกใน dropdown filter หน้าเว็บ

    # อ่านค่า filter จาก URL เช่น ?category=C001&light=low&search=มอนสเตอร่า
    category_id = request.GET.get('category') or ''
    light = request.GET.get('light') or ''
    water = request.GET.get('water') or ''
    humidity = request.GET.get('humidity') or ''
    search = request.GET.get('search') or ''

    # กรองพืชตามค่าที่ผู้ใช้เลือก (จะ filter เฉพาะฟิลด์ที่มีค่าจริงเท่านั้น)
    if category_id:
        plants = plants.filter(category_id=category_id)
    if light:
        plants = plants.filter(light=light)
    if water:
        plants = plants.filter(water=water)
    if humidity:
        plants = plants.filter(humidity=humidity)
    if search:
        plants = plants.filter(plant_name__icontains=search)  # ค้นหาชื่อพืชแบบไม่สนตัวพิมพ์เล็ก/ใหญ่

    # บันทึก Search Log + สร้าง FAQ อัตโนมัติเมื่อมีการค้นหา
    # เงื่อนไข: ต้องมีการเลือก filter อย่างน้อย 1 ตัว (ไม่นับ search แบบพิมพ์ชื่อพืชอิสระ)
    if any([light, water, humidity, category_id]):
        # ถ้ามี category_id ให้ดึง object จริงมาด้วย เพราะ record_search ต้องการ object ไม่ใช่ id string
        category_obj = PlantCategory.objects.filter(category_id=category_id).first() if category_id else None
        record_search(
            filter_light=light or None,
            filter_water=water or None,
            filter_humidity=humidity or None,
            filter_category=category_obj,
        )

    # Pagination — แบ่งหน้ารายการพืช หน้าละ 9 รายการ เรียงตาม plant_id
    paginator = Paginator(plants.order_by('plant_id'), 9)
    plants_page = paginator.get_page(request.GET.get('page'))  # อ่านเลขหน้าจาก ?page=

    # FAQ เรียงตามจำนวนการค้นหาสูงสุด
    # ดึง 5 อันดับ SearchSummary ที่มี FAQ ผูกอยู่แล้ว (faq__isnull=False) เรียงจากค้นหาบ่อยสุดไปน้อยสุด
    popular_faqs = (
        SearchSummary.objects
        .filter(faq__isnull=False)
        .select_related('faq')
        .order_by('-search_count')[:5]
    )

    # render หน้า index.html พร้อมส่งข้อมูลทั้งหมดที่จำเป็นไปแสดงผล
    return render(request, "index.html", {
        "plants": plants_page,
        "categories": categories,
        "popular_faqs": popular_faqs,
        # ส่งค่า filter ที่เลือกไว้กลับไปด้วย เพื่อให้ dropdown/ช่องค้นหาแสดงค่าที่เลือกล่าสุดค้างไว้
        "selected_category": category_id,
        "selected_light": light,
        "selected_water": water,
        "selected_humidity": humidity,
        "search": search,
    })


def chat(request):
    # แสดงหน้าแชท (แค่ render template เปล่าๆ ตัว logic การคุยจริงอยู่ที่ chat_with_llm)
    return render(request, "chat.html")


@csrf_exempt
def chat_with_llm(request):
    # endpoint รับข้อความจากผู้ใช้
    # แล้วส่งให้ LLM พร้อมข้อมูลอ้างอิงจาก DB

    if request.method != 'POST':
        return JsonResponse({
            'reply': 'Method not allowed'
        }, status=405)

    user_input = request.POST.get('message', '').strip()

    # =====================================================
    # 1. ตรวจสอบและแก้ข้อความกรณีพิมพ์สลับภาษา
    # =====================================================

    normalized_input = user_input

    matched_plant_names = match_plant_names(user_input)

    if matched_plant_names:
        # ใช้ชื่อพืชจริงจากฐานข้อมูล
        normalized_input = " ".join(
            sorted(matched_plant_names)
        )

    try:

        # =====================================================
        # 2. ค้นหาข้อมูลพืชจากฐานข้อมูล
        # =====================================================

        context_data = get_plant_context(normalized_input)

        # =====================================================
        # 3. ส่งข้อมูลให้ OpenAI
        # =====================================================

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""
คุณคือผู้ช่วยแนะนำต้นไม้ ตอบภาษาไทยอย่างเป็นกันเองและกระชับ

[ข้อมูลอ้างอิงจากฐานข้อมูล]
{context_data}

[กฎเหล็กในการตอบคำถาม - ต้องปฏิบัติตามอย่างเคร่งครัด]:

1. **ใช้อ้างอิงจากฐานข้อมูลเท่านั้น**
ห้ามคิดชื่อต้นไม้เอง ห้ามใช้ความรู้ภายนอกเด็ดขาด!
ให้ใช้เฉพาะรายชื่อต้นไม้ที่ปรากฏอยู่ใน
[ข้อมูลอ้างอิงจากฐานข้อมูล] ด้านบนเท่านั้น

2. **กรณีไม่พบข้อมูล**
หากข้อมูลอ้างอิงระบุว่า
"ไม่พบข้อมูลต้นไม้..."
ให้ตอบว่า:

"ขออภัยครับ ไม่พบข้อมูลต้นไม้ที่ตรงตามเงื่อนไขในระบบครับ"

3. **กรณีพบข้อมูลต้นไม้**
- หากผู้ใช้พิมพ์ค้นหาด้วยคุณสมบัติ/หมวดหมู่ เช่น "แสงน้อย", "น้ำปานกลาง", "น้ำน้อย", "ไม้ล้มลุก" ให้แสดงรายชื่อต้นไม้จากข้อมูลอ้างอิงให้ครบทุกต้นที่มีอยู่ ห้ามตัดรายชื่อออก และห้ามเพิ่มต้นไม้ที่ไม่มีในข้อมูลอ้างอิง โดยดึงชื่อจาก DB มาตรงๆ
- หากข้อมูลอ้างอิงมีหลายรายการ ให้แสดงทุกรายการตามข้อมูลอ้างอิง ไม่จำกัดจำนวนรายการ

- หากผู้ใช้ขอคำแนะนำ เช่น "ปลูกง่าย", "ดูแลง่าย", "เหมาะกับมือใหม่" หรือคำถามลักษณะใกล้เคียง ให้พิจารณาจากข้อมูลต้นไม้ทั้งหมดที่ได้รับจากฐานข้อมูล แล้วเลือกต้นไม้ที่เหมาะสม 1 ต้น โดยห้ามสร้างต้นไม้ที่ไม่มีอยู่ในข้อมูลอ้างอิง

4. **กรณีคำทักทาย**
หากพิมพ์แค่คำทักทาย
ให้ตอบรับสุภาพและบอกว่าพร้อมแนะนำต้นไม้จากฐานข้อมูล
"""
                },

                {
                    "role": "user",
                    "content": normalized_input
                },
            ],
            temperature=0.2,
        )

        # =====================================================
        # 4. ส่งผลกลับไปยังหน้าเว็บ
        # =====================================================

        return JsonResponse({
            'reply': completion.choices[0].message.content,
            'normalized_message': normalized_input
        })

    except Exception as e:

        print(f"Error: {e}")

        return JsonResponse({
            'reply': 'ขออภัยครับ ระบบประมวลผลขัดข้อง',
            'normalized_message': normalized_input
        }, status=500)


# ─────────────────────────────────────────────
#  5. Authentication Views (Custom Session)
#     ระบบ login/logout แบบกำหนดเอง (ไม่ได้ใช้ Django auth framework มาตรฐาน)
# ─────────────────────────────────────────────
def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # ตรวจสอบ username/password ตรงกับข้อมูลใน Admin model หรือไม่
            # หมายเหตุ: เทียบ password แบบ plain text ตรงๆ (ไม่ได้ hash) ตามที่ออกแบบไว้ใน model
            admin_user = Admin.objects.filter(username=username, password=password).first()
            if admin_user:
                # login สำเร็จ: เก็บ admin_id และ username ไว้ใน session เพื่อใช้ตรวจสอบสิทธิ์ภายหลัง
                request.session['admin_id'] = admin_user.admin_id
                request.session['admin_username'] = admin_user.username
                return redirect('management')  # พาไปหน้าจัดการข้อมูล
            else:
                error_message = "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
    else:
        form = AdminLoginForm()  # GET request: แสดงฟอร์ม login เปล่าๆ

    return render(request, 'login.html', {'form': form, 'error': error_message})


def logout_view(request):
    # ล้างข้อมูลทั้งหมดใน session (ทำให้ admin_id หายไป = ถือว่า logout แล้ว)
    request.session.flush()
    return redirect('/')  # กลับไปหน้าแรก


# ─────────────────────────────────────────────
#  6. Management Views (Admin Scope)
#     views ทั้งหมดในหมวดนี้ต้อง login ก่อน (ครอบด้วย @admin_required)
# ─────────────────────────────────────────────
@admin_required
def management_view(request):
    # หน้าหลักของระบบจัดการหลัง login: มีแท็บ (tab) ย่อยสำหรับ plants/categories/faqs/admins
    tab = request.GET.get('tab', 'plants')  # ค่าเริ่มต้นถ้าไม่ระบุ tab คือ 'plants'
    plants = Plant.objects.select_related('category', 'admin').all()
    categories = PlantCategory.objects.select_related('admin').all()
    faqs = Faq.objects.all()
    admins = Admin.objects.all()

    return render(request, 'management.html', {
        'tab': tab,
        'plants': plants,
        'categories': categories,
        'faqs': faqs,
        'admins': admins,
    })


@admin_required
def plant_add(request):
    # ดึงข้อมูล admin ที่ login อยู่ตอนนี้ (จาก session) เพื่อผูกเป็นเจ้าของพืชที่จะเพิ่ม
    current_admin = get_object_or_404(Admin, admin_id=request.session['admin_id'])
    if request.method == 'POST':
        form = PlantForm(request.POST)
        if form.is_valid():
            # commit=False: สร้าง object ในหน่วยความจำก่อน ยังไม่บันทึกลง DB
            # เพื่อให้เราเซ็ตค่า admin ก่อน แล้วค่อย save() จริงอีกที
            plant = form.save(commit=False)
            plant.admin = current_admin
            plant.save()
            messages.success(request, f'เพิ่มพืช "{plant.plant_name}" เรียบร้อยแล้ว')
            return redirect('/management/?tab=plants')  # เสร็จแล้วกลับไปหน้ารายการพืช
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลในฟอร์มอีกครั้ง')
    else:
        form = PlantForm()  # GET request: แสดงฟอร์มเปล่าสำหรับกรอกข้อมูลใหม่
    return render(request, 'plant_form.html', {'form': form, 'title': 'เพิ่มข้อมูลพืช'})


@admin_required
def plant_edit(request, pk):
    # ดึงพืชตามรหัส pk (เช่น P001) ถ้าไม่เจอจะแสดงหน้า 404 อัตโนมัติ
    plant = get_object_or_404(Plant, pk=pk)
    if request.method == 'POST':
        # ผูกฟอร์มกับ instance เดิม (plant) เพื่อแก้ไขข้อมูล แทนที่จะสร้างใหม่
        form = PlantForm(request.POST, instance=plant)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขข้อมูลพืช "{plant.plant_name}" เรียบร้อยแล้ว')
            return redirect('/management/?tab=plants')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลในฟอร์มอีกครั้ง')
    else:
        form = PlantForm(instance=plant)  # GET request: แสดงฟอร์มพร้อมข้อมูลเดิมของพืชนี้
    return render(request, 'plant_form.html', {'form': form, 'title': 'แก้ไขข้อมูลพืช'})


@admin_required
def plant_delete(request, pk):
    # ลบพืชตามรหัส pk ทันที (ไม่มีหน้ายืนยันแยกต่างหากใน view นี้)
    plant = get_object_or_404(Plant, pk=pk)
    plant_name = plant.plant_name
    plant.delete()
    messages.success(request, f'ลบพืช "{plant_name}" เรียบร้อยแล้ว')
    return redirect('/management/?tab=plants')


@admin_required
def category_add(request):
    # เหมือน plant_add แต่สำหรับหมวดหมู่พืช
    current_admin = get_object_or_404(Admin, admin_id=request.session['admin_id'])
    if request.method == 'POST':
        form = PlantCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.admin = current_admin  # ผูกหมวดหมู่กับ admin ที่สร้าง
            cat.save()
            messages.success(request, f'เพิ่มหมวดหมู่ "{cat.category_name}" เรียบร้อยแล้ว')
            return redirect('/management/?tab=categories')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลในฟอร์มอีกครั้ง')
    else:
        form = PlantCategoryForm()
    return render(request, 'category_form.html', {'form': form, 'title': 'เพิ่มหมวดหมู่พืช'})


@admin_required
def category_edit(request, pk):
    cat = get_object_or_404(PlantCategory, pk=pk)
    if request.method == 'POST':
        form = PlantCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขหมวดหมู่ "{cat.category_name}" เรียบร้อยแล้ว')
            return redirect('/management/?tab=categories')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลในฟอร์มอีกครั้ง')
    else:
        form = PlantCategoryForm(instance=cat)
    return render(request, 'category_form.html', {'form': form, 'title': 'แก้ไขหมวดหมู่พืช'})


@admin_required
def category_delete(request, pk):
    # หมายเหตุ: PlantCategory ผูกกับ Plant แบบ CASCADE ดังนั้นลบ category นี้จะลบพืชในหมวดนี้ทั้งหมดไปด้วย
    cat = get_object_or_404(PlantCategory, pk=pk)
    cat_name = cat.category_name
    cat.delete()
    messages.success(request, f'ลบหมวดหมู่ "{cat_name}" เรียบร้อยแล้ว (พืชในหมวดนี้ถูกลบไปด้วย)')
    return redirect('/management/?tab=categories')


@admin_required
def faq_delete(request, pk):
    # ลบ FAQ ตามรหัส pk (ทั้ง FAQ ที่ admin สร้างเองและที่ระบบ auto-gen ก็ลบได้ผ่าน view นี้)
    faq = get_object_or_404(Faq, pk=pk)
    faq_title = faq.title
    faq.delete()
    messages.success(request, f'ลบ FAQ "{faq_title}" เรียบร้อยแล้ว')
    return redirect('/management/?tab=faqs')


@admin_required
def admin_add(request):
    # เพิ่มผู้ดูแลระบบใหม่ (ไม่ต้องผูกกับ admin คนปัจจุบัน เพราะ Admin ไม่มี FK ถึงตัวเอง)
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            admin_obj = form.save()
            messages.success(request, f'เพิ่มผู้ดูแลระบบ "{admin_obj.username}" เรียบร้อยแล้ว')
            return redirect('/management/?tab=admins')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลในฟอร์มอีกครั้ง')
    else:
        form = AdminUserForm()
    return render(request, 'admin_form.html', {'form': form, 'title': 'เพิ่มผู้ดูแลระบบ'})


@admin_required
def admin_edit(request, pk):
    admin_obj = get_object_or_404(Admin, pk=pk)
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=admin_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขข้อมูลผู้ดูแลระบบ "{admin_obj.username}" เรียบร้อยแล้ว')
            return redirect('/management/?tab=admins')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลในฟอร์มอีกครั้ง')
    else:
        form = AdminUserForm(instance=admin_obj)
    return render(request, 'admin_form.html', {'form': form, 'title': 'แก้ไขข้อมูลผู้ดูแลระบบ'})