from django.db import models

# Create your models here.

from django.db import models


# ─────────────────────────────────────────────
#  ฟังก์ชันสำหรับ gen รหัสรูปแบบ P001, C001, A001, F001, L001, S001
#  ใช้ร่วมกันในทุกโมเดลที่มี primary key เป็นรหัส (ไม่ใช้ auto-increment ปกติ)
# ─────────────────────────────────────────────
def generate_code(model, field_name, prefix, width=3):
    """
    หา running number ล่าสุดของ prefix นั้น แล้วบวก 1
    เช่น generate_code(Plant, 'plant_id', 'P') -> 'P001', 'P002', ...

    Parameters:
        model      : คลาสโมเดลที่จะ query (เช่น Plant, Admin, Faq)
        field_name : ชื่อฟิลด์ที่เป็น primary key แบบรหัส (เช่น 'plant_id')
        prefix     : ตัวอักษรนำหน้ารหัส (เช่น 'P', 'C', 'A', 'F', 'L', 'S')
        width      : จำนวนหลักตัวเลขที่ต้องการ (default = 3 หลัก เช่น 001)
    """
    # ค้นหา record ล่าสุดที่ field_name ขึ้นต้นด้วย prefix ที่กำหนด
    # แล้วเรียงจากมากไปน้อย (-field_name) เพื่อเอาตัวที่มีเลขสูงสุด
    last_obj = model.objects.filter(
        **{f"{field_name}__startswith": prefix}
    ).order_by(f"-{field_name}").first()

    # ถ้ายังไม่มี record ไหนเลย ให้เริ่มที่เลข 1 (เช่น P001)
    if not last_obj:
        return f"{prefix}{1:0{width}d}"

    # ถ้ามี record อยู่แล้ว ให้ดึงรหัสล่าสุดออกมา ตัด prefix ออก
    # แปลงเป็นตัวเลข แล้วบวก 1 เพื่อสร้างรหัสถัดไป
    last_code = getattr(last_obj, field_name)
    last_number = int(last_code.replace(prefix, ""))
    return f"{prefix}{last_number + 1:0{width}d}"


# ═════════════════════════════════════════════
# 1. admin — ตารางเก็บข้อมูลผู้ดูแลระบบ
#    ใช้สำหรับ login เข้าหน้า management และผูกเป็นเจ้าของข้อมูล plant / category
# ═════════════════════════════════════════════
class Admin(models.Model):
    # primary key แบบรหัส เช่น A001 (editable=False คือแก้ผ่านฟอร์มไม่ได้ ต้อง gen เอง)
    admin_id = models.CharField(primary_key=True, max_length=11, editable=False)
    username = models.CharField(max_length=50, unique=True)  # ชื่อผู้ใช้ ต้องไม่ซ้ำกัน
    email = models.EmailField(max_length=50)
    password = models.CharField(max_length=25)  # ควร hash ด้วย make_password ก่อนบันทึก

    class Meta:
        db_table = "admin"  # กำหนดชื่อตารางจริงใน database เป็น "admin"
        verbose_name = "ผู้ดูแลระบบ"  # ชื่อที่แสดงใน Django admin

    def save(self, *args, **kwargs):
        # ถ้ายังไม่มี admin_id (สร้าง record ใหม่) ให้ gen รหัสอัตโนมัติ เช่น A001
        if not self.admin_id:
            self.admin_id = generate_code(Admin, "admin_id", "A")
        super().save(*args, **kwargs)  # เรียก save() ปกติของ Django เพื่อบันทึกลง DB จริง

    def __str__(self):
        # ข้อความที่แสดงเวลา print object หรือแสดงใน Django admin dropdown
        return f"{self.admin_id} - {self.username}"


# ═════════════════════════════════════════════
# 2. plant_category — ตารางเก็บข้อมูลหมวดหมู่พืช
#    เช่น ไม้ล้มลุก, ไม้พุ่ม, ไม้เลื้อย ฯลฯ
# ═════════════════════════════════════════════
class PlantCategory(models.Model):
    category_id = models.CharField(primary_key=True, max_length=11, editable=False)  # เช่น C001
    category_name = models.CharField(max_length=50)  # ชื่อหมวดหมู่ เช่น "ไม้เลื้อย"
    detail = models.TextField(blank=True, null=True)  # คำอธิบายหมวดหมู่ (ใส่หรือไม่ใส่ก็ได้)
    # FK ไปยัง Admin ผู้สร้างหมวดหมู่นี้ (1 admin สร้างได้หลาย category)
    # ถ้า admin ถูกลบ ให้ลบ category ที่ผูกอยู่ด้วย (CASCADE)
    admin = models.ForeignKey(
        Admin, db_column="admin_id", on_delete=models.CASCADE,
        related_name="plant_categories"
    )

    class Meta:
        db_table = "plant_category"
        verbose_name = "หมวดหมู่พืช"

    def save(self, *args, **kwargs):
        # gen รหัส category_id อัตโนมัติ เช่น C001 ถ้ายังไม่มี
        if not self.category_id:
            self.category_id = generate_code(PlantCategory, "category_id", "C")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category_id} - {self.category_name}"


# ═════════════════════════════════════════════
# 3. plant — ตารางเก็บข้อมูลพืชแต่ละต้น
#    เก็บคุณสมบัติด้านแสง/น้ำ/ความชื้น เพื่อใช้ filter และใช้เป็นข้อมูลให้ AI แนะนำ
# ═════════════════════════════════════════════
class Plant(models.Model):
    # กำหนดตัวเลือกสำหรับ Light, Water, Humidity
    # แต่ละ tuple คือ (ค่าที่เก็บใน DB, ค่าที่แสดงผลให้ผู้ใช้เห็น)
    LIGHT_CHOICES = [
        ('low', 'แสงน้อย'),
        ('medium', 'แสงปานกลาง'),
        ('high', 'แสงมาก'),
    ]

    WATER_CHOICES = [
        ('low', 'น้ำน้อย'),
        ('medium', 'น้ำปานกลาง'),
        ('high', 'น้ำมาก'),
    ]

    HUMIDITY_CHOICES = [
        ('low', 'ความชื้นต่ำ'),
        ('medium', 'ความชื้นปานกลาง'),
        ('high', 'ความชื้นสูง'),
    ]

    plant_id = models.CharField(primary_key=True, max_length=11, editable=False)  # เช่น P001
    plant_name = models.CharField(max_length=50)  # ชื่อพืช

    # ฟิลด์ choices ทั้งสามนี้ เก็บค่าเป็น string 'low'/'medium'/'high'
    # แต่จะแสดงผลเป็นภาษาไทยผ่าน get_light_display(), get_water_display(), get_humidity_display()
    light = models.CharField(max_length=10, choices=LIGHT_CHOICES)
    water = models.CharField(max_length=10, choices=WATER_CHOICES)
    humidity = models.CharField(max_length=10, choices=HUMIDITY_CHOICES)

    description = models.TextField(blank=True, null=True)  # รายละเอียด/คำอธิบายเพิ่มเติมของพืช
    # FK ไปยังหมวดหมู่ที่พืชต้นนี้สังกัดอยู่ (1 category มีได้หลาย plant)
    category = models.ForeignKey(
        PlantCategory, db_column="category_id", on_delete=models.CASCADE,
        related_name="plants"
    )
    # FK ไปยัง admin ผู้เพิ่มข้อมูลพืชนี้
    admin = models.ForeignKey(
        Admin, db_column="admin_id", on_delete=models.CASCADE,
        related_name="plants"
    )

    class Meta:
        db_table = "plant"
        verbose_name = "พืช"

    def save(self, *args, **kwargs):
        # gen รหัส plant_id อัตโนมัติ เช่น P001 ถ้ายังไม่มี
        if not self.plant_id:
            self.plant_id = generate_code(Plant, "plant_id", "P")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plant_id} - {self.plant_name}"


# ═════════════════════════════════════════════
# 4. faq — ตารางเก็บข้อมูลคำถามที่พบบ่อย
#    บางส่วนสร้างโดย admin เอง บางส่วนถูกสร้างอัตโนมัติจากการค้นหาซ้ำๆ (ดูฟังก์ชัน _auto_generate_faq ด้านล่าง)
# ═════════════════════════════════════════════
class Faq(models.Model):
    faq_id = models.CharField(primary_key=True, max_length=11, editable=False)  # เช่น F001
    title = models.CharField(max_length=50)  # หัวข้อคำถาม
    answer_text = models.TextField()  # คำตอบ
    created_at = models.DateTimeField(auto_now_add=True)  # วันเวลาที่สร้าง (ตั้งค่าอัตโนมัติครั้งแรกที่ save)

    class Meta:
        db_table = "faq"
        verbose_name = "คำถามที่พบบ่อย"

    def save(self, *args, **kwargs):
        # gen รหัส faq_id อัตโนมัติ เช่น F001 ถ้ายังไม่มี
        if not self.faq_id:
            self.faq_id = generate_code(Faq, "faq_id", "F")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.faq_id} - {self.title}"


# ═════════════════════════════════════════════
# 5. search_log — ตารางเก็บประวัติการค้นหาแบบดิบ (บันทึกทุกครั้งที่มีการค้นหา)
#    ใช้เป็น log ดิบ ไม่ได้เอาไว้สรุปผล (การสรุปผลอยู่ที่ SearchSummary)
# ═════════════════════════════════════════════
class SearchLog(models.Model):
    log_id = models.CharField(primary_key=True, max_length=11, editable=False)  # เช่น L001
    # เก็บค่า filter ที่ผู้ใช้เลือกตอนค้นหา (อาจว่างได้ถ้าผู้ใช้ไม่ได้เลือก)
    filter_light = models.CharField(max_length=10, blank=True, null=True)
    filter_water = models.CharField(max_length=10, blank=True, null=True)
    filter_humidity = models.CharField(max_length=10, blank=True, null=True)
    # FK ไปยังหมวดหมู่ที่ค้นหา (ถ้า category ถูกลบ ให้ค่านี้กลายเป็น NULL แทนที่จะลบ log ทิ้ง)
    category = models.ForeignKey(
        PlantCategory, db_column="category_id", on_delete=models.SET_NULL,
        related_name="search_logs", blank=True, null=True
    )
    searched_at = models.DateTimeField(auto_now_add=True)  # เวลาที่ค้นหา (ตั้งอัตโนมัติตอนสร้าง)

    class Meta:
        db_table = "search_log"
        verbose_name = "ประวัติการค้นหา"

    def save(self, *args, **kwargs):
        if not self.log_id:
            self.log_id = generate_code(SearchLog, "log_id", "L")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.log_id} - {self.searched_at}"


# ═════════════════════════════════════════════
# 6. search_summary — ตารางเก็บสรุปผลการค้นหา
#    รวมยอดจำนวนครั้งที่มีการค้นหาด้วย filter combo เดียวกัน (light/water/humidity/category)
#    เมื่อค้นหาซ้ำถึงจำนวนที่กำหนด (FAQ_THRESHOLD) จะสร้าง FAQ อัตโนมัติและผูกไว้ที่ summary นี้
# ═════════════════════════════════════════════
class SearchSummary(models.Model):
    summary_id = models.CharField(primary_key=True, max_length=11, editable=False)  # เช่น S001
    # filter combo เดียวกับ SearchLog แต่ในตารางนี้แต่ละ combo จะมีแค่ 1 แถว (unique โดย logic ใน record_search)
    filter_light = models.CharField(max_length=10, blank=True, null=True)
    filter_water = models.CharField(max_length=10, blank=True, null=True)
    filter_humidity = models.CharField(max_length=10, blank=True, null=True)
    category = models.ForeignKey(
        PlantCategory, db_column="category_id", on_delete=models.SET_NULL,
        related_name="search_summaries", blank=True, null=True
    )
    search_count = models.IntegerField(default=0)  # จำนวนครั้งที่มีการค้นหาด้วย filter combo นี้
    last_searched = models.DateTimeField(auto_now=True)  # เวลาค้นหาล่าสุด (อัปเดตทุกครั้งที่ save)
    # FK ไปยัง FAQ ที่ถูกสร้างอัตโนมัติจาก combo นี้ (ถ้ายังไม่ถึง threshold ค่านี้จะเป็น NULL)
    faq = models.ForeignKey(
        Faq, db_column="faq_id", on_delete=models.SET_NULL,
        related_name="search_summaries", blank=True, null=True
    )

    class Meta:
        db_table = "search_summary"
        verbose_name = "สรุปผลการค้นหา"

    def save(self, *args, **kwargs):
        if not self.summary_id:
            self.summary_id = generate_code(SearchSummary, "summary_id", "S")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.summary_id} ({self.search_count} ครั้ง)"


# ─────────────────────────────────────────────
#  แก้ไข: ฟังก์ชันสำหรับบันทึก Search Log
#  และสร้าง FAQ อัตโนมัติเมื่อมีการค้นหาซ้ำกันเกินกำหนด
# ─────────────────────────────────────────────

FAQ_THRESHOLD = 5  # เปลี่ยนตรงนี้ที่เดียวถ้าต้องการปรับ จำนวนครั้งที่ต้องค้นซ้ำก่อนจะสร้าง FAQ อัตโนมัติ

# Dict สำหรับแปลงค่า 'low'/'medium'/'high' ที่เก็บใน DB ให้เป็นข้อความภาษาไทยสั้นๆ
# ใช้ตอนประกอบข้อความหัวข้อ FAQ (ต่างจาก LIGHT_CHOICES/WATER_CHOICES/HUMIDITY_CHOICES ใน Plant
# ตรงที่อันนี้ใช้คำสั้นกว่า เพื่อเอาไปต่อกับคำว่า "แสง"/"น้ำ"/"ความชื้น" ข้างหน้า)
LIGHT_LABELS = {'low': 'น้อย', 'medium': 'ปานกลาง', 'high': 'มาก'}
WATER_LABELS = {'low': 'น้อย', 'medium': 'ปานกลาง', 'high': 'มาก'}
HUMIDITY_LABELS = {'low': 'ต่ำ', 'medium': 'ปานกลาง', 'high': 'สูง'}


def record_search(filter_light=None, filter_water=None, filter_humidity=None, filter_category=None):
    """บันทึก log ดิบ + อัปเดต summary + auto gen FAQ ถ้าถึง threshold"""

    # 1. บันทึก SearchLog (ดิบ ไม่ต้องแก้)
    #    เก็บทุกครั้งที่มีการค้นหา ไม่สนใจว่าจะซ้ำ combo เดิมหรือไม่ (ใช้เป็นประวัติดิบ)
    SearchLog.objects.create(
        filter_light=filter_light,
        filter_water=filter_water,
        filter_humidity=filter_humidity,
        category=filter_category
    )

    # 2. อัปเดตหรือสร้าง SearchSummary
    #    get_or_create จะหา row ที่มี filter combo (light, water, humidity, category) ตรงกันเป๊ะ
    #    ถ้าไม่เจอ จะสร้างใหม่ (created=True), ถ้าเจอ จะได้ row เดิมกลับมา (created=False)
    summary, created = SearchSummary.objects.get_or_create(
        filter_light=filter_light,
        filter_water=filter_water,
        filter_humidity=filter_humidity,
        category=filter_category
    )
    if not created:
        # ถ้ามี summary combo นี้อยู่แล้ว ให้บวกจำนวนครั้งเพิ่มไป 1
        summary.search_count += 1
    else:
        # ถ้าเพิ่งสร้างใหม่ ให้เริ่มนับที่ 1 (การเรียก create เป็นการค้นหาครั้งแรก)
        summary.search_count = 1
    summary.save()  # บันทึกการเปลี่ยนแปลง search_count / last_searched ลง DB

    # 3. auto gen FAQ ถ้าถึง threshold และยังไม่มี FAQ ผูกอยู่
    #    เงื่อนไข: จำนวนค้นหา >= FAQ_THRESHOLD (ค่าเริ่มต้น 5 ครั้ง) และยังไม่เคยสร้าง FAQ ให้ combo นี้มาก่อน
    if summary.search_count >= FAQ_THRESHOLD and summary.faq is None:
        _auto_generate_faq(summary)


def _auto_generate_faq(summary: "SearchSummary"):
    """สร้าง FAQ อัตโนมัติจาก filter combo ใน summary โดยดึงรายชื่อพืชจริงมาใส่คำตอบ"""

    # --- สร้างข้อความเงื่อนไข (เฉพาะที่มีค่าจริง ไม่ใช่ None) ---
    # ประกอบ list ของข้อความเงื่อนไข เช่น "แสงน้อย", "น้ำปานกลาง" เพื่อเอาไปตั้งเป็นหัวข้อ FAQ
    parts = []
    if summary.filter_light:
        parts.append(f"แสง{LIGHT_LABELS.get(summary.filter_light, summary.filter_light)}")
    if summary.filter_water:
        parts.append(f"น้ำ{WATER_LABELS.get(summary.filter_water, summary.filter_water)}")
    if summary.filter_humidity:
        parts.append(f"ความชื้น{HUMIDITY_LABELS.get(summary.filter_humidity, summary.filter_humidity)}")
    if summary.category:
        parts.append(f"หมวด{summary.category.category_name}")

    # รวมเงื่อนไขทั้งหมดด้วย ", " ถ้าไม่มีเงื่อนไขเลยให้ใช้คำว่า "ทุกประเภท" แทน
    condition_str = ", ".join(parts) if parts else "ทุกประเภท"

    # --- query พืชจริงที่ตรงกับเงื่อนไข ---
    # เริ่มจากพืชทั้งหมด แล้วค่อยๆ filter ตามเงื่อนไขที่ summary มี (เฉพาะที่ไม่ใช่ None)
    plants = Plant.objects.all()
    if summary.filter_light:
        plants = plants.filter(light=summary.filter_light)
    if summary.filter_water:
        plants = plants.filter(water=summary.filter_water)
    if summary.filter_humidity:
        plants = plants.filter(humidity=summary.filter_humidity)
    if summary.category:
        plants = plants.filter(category=summary.category)

    # รวมชื่อพืชทั้งหมดที่เจอด้วย ", " ถ้าไม่เจอเลยให้ใช้ข้อความแจ้งว่าไม่มีข้อมูล
    answer = ", ".join(p.plant_name for p in plants) or "ยังไม่มีข้อมูลพืชที่ตรงกับเงื่อนไขนี้ในระบบ"

    # สร้าง FAQ ใหม่ โดยตัด title ไม่ให้เกิน 50 ตัวอักษร (ตาม max_length ของฟิลด์ title)
    faq = Faq.objects.create(
        title=f"พืชที่เหมาะกับ {condition_str}"[:50],  # ตัดไม่ให้เกิน max_length=50
        answer_text=f"พืชที่แนะนำ ได้แก่: {answer}",
    )

    # ผูก FAQ ที่สร้างใหม่กลับเข้ากับ summary นี้ เพื่อไม่ให้สร้าง FAQ ซ้ำอีกในครั้งถัดไป
    summary.faq = faq
    summary.save()