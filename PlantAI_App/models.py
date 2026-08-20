from django.db import models

# Create your models here.

from django.db import models



#ฟังก์ชันสำหรับ gen รหัสรูปแบบ P001, C001, A001, F001, L001, S001
def generate_code(model, field_name, prefix, width=3):
    """
    หา running number ล่าสุดของ prefix นั้น แล้วบวก 1
    เช่น generate_code(Plant, 'plant_id', 'P') -> 'P001', 'P002', ...
    """
    last_obj = model.objects.filter(
        **{f"{field_name}__startswith": prefix}
    ).order_by(f"-{field_name}").first()

    if not last_obj:
        return f"{prefix}{1:0{width}d}"

    last_code = getattr(last_obj, field_name)
    last_number = int(last_code.replace(prefix, ""))
    return f"{prefix}{last_number + 1:0{width}d}"



# 1. admin — ตารางเก็บข้อมูลผู้ดูแลระบบ
class Admin(models.Model):
    admin_id = models.CharField(primary_key=True, max_length=11, editable=False)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=50)
    password = models.CharField(max_length=25)  # ควร hash ด้วย make_password ก่อนบันทึก

    class Meta:
        db_table = "admin"
        verbose_name = "ผู้ดูแลระบบ"

    def save(self, *args, **kwargs):
        if not self.admin_id:
            self.admin_id = generate_code(Admin, "admin_id", "A")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.admin_id} - {self.username}"



# 2. plant_category — ตารางเก็บข้อมูลหมวดหมู่พืช
class PlantCategory(models.Model):
    category_id = models.CharField(primary_key=True, max_length=11, editable=False)
    category_name = models.CharField(max_length=50)
    detail = models.TextField(blank=True, null=True)
    admin = models.ForeignKey(
        Admin, db_column="admin_id", on_delete=models.CASCADE,
        related_name="plant_categories"
    )

    class Meta:
        db_table = "plant_category"
        verbose_name = "หมวดหมู่พืช"

    def save(self, *args, **kwargs):
        if not self.category_id:
            self.category_id = generate_code(PlantCategory, "category_id", "C")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category_id} - {self.category_name}"


# 3. plant — ตารางเก็บข้อมูลพืช
class Plant(models.Model):
    # กำหนดตัวเลือกสำหรับ Light, Water, Humidity
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

    plant_id = models.CharField(primary_key=True, max_length=11, editable=False)
    plant_name = models.CharField(max_length=50)
    
    # ใช้ choices และขยาย max_length เป็น 20 เพื่อความปลอดภัย
    light = models.CharField(max_length=10, choices=LIGHT_CHOICES)
    water = models.CharField(max_length=10, choices=WATER_CHOICES)
    humidity = models.CharField(max_length=10, choices=HUMIDITY_CHOICES)
    
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        PlantCategory, db_column="category_id", on_delete=models.CASCADE,
        related_name="plants"
    )
    admin = models.ForeignKey(
        Admin, db_column="admin_id", on_delete=models.CASCADE,
        related_name="plants"
    )

    class Meta:
        db_table = "plant"
        verbose_name = "พืช"

    def save(self, *args, **kwargs):
        if not self.plant_id:
            self.plant_id = generate_code(Plant, "plant_id", "P")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plant_id} - {self.plant_name}"



# 4. faq — ตารางเก็บข้อมูลคำถามที่พบบ่อย
class Faq(models.Model):
    faq_id = models.CharField(primary_key=True, max_length=11, editable=False)
    title = models.CharField(max_length=50)
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "faq"
        verbose_name = "คำถามที่พบบ่อย"

    def save(self, *args, **kwargs):
        if not self.faq_id:
            self.faq_id = generate_code(Faq, "faq_id", "F")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.faq_id} - {self.title}"



# 5. search_log — ตารางเก็บประวัติการค้นหา
class SearchLog(models.Model):
    log_id = models.CharField(primary_key=True, max_length=11, editable=False)
    filter_light = models.CharField(max_length=10, blank=True, null=True)
    filter_water = models.CharField(max_length=10, blank=True, null=True)
    filter_humidity = models.CharField(max_length=10, blank=True, null=True)
    category = models.ForeignKey(
        PlantCategory, db_column="category_id", on_delete=models.SET_NULL,
        related_name="search_logs", blank=True, null=True
    )
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_log"
        verbose_name = "ประวัติการค้นหา"

    def save(self, *args, **kwargs):
        if not self.log_id:
            self.log_id = generate_code(SearchLog, "log_id", "L")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.log_id} - {self.searched_at}"



# 6. search_summary — ตารางเก็บสรุปผลการค้นหา
class SearchSummary(models.Model):
    summary_id = models.CharField(primary_key=True, max_length=11, editable=False)
    filter_light = models.CharField(max_length=10, blank=True, null=True)
    filter_water = models.CharField(max_length=10, blank=True, null=True)
    filter_humidity = models.CharField(max_length=10, blank=True, null=True)
    category = models.ForeignKey(
        PlantCategory, db_column="category_id", on_delete=models.SET_NULL,
        related_name="search_summaries", blank=True, null=True
    )
    search_count = models.IntegerField(default=0)
    last_searched = models.DateTimeField(auto_now=True)
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

FAQ_THRESHOLD = 5  # เปลี่ยนตรงนี้ที่เดียวถ้าต้องการปรับ

LIGHT_LABELS = {'low': 'น้อย', 'medium': 'ปานกลาง', 'high': 'มาก'}
WATER_LABELS = {'low': 'น้อย', 'medium': 'ปานกลาง', 'high': 'มาก'}
HUMIDITY_LABELS = {'low': 'ต่ำ', 'medium': 'ปานกลาง', 'high': 'สูง'}


def record_search(filter_light=None, filter_water=None, filter_humidity=None, filter_category=None):
    """บันทึก log ดิบ + อัปเดต summary + auto gen FAQ ถ้าถึง threshold"""

    # 1. บันทึก SearchLog (ดิบ ไม่ต้องแก้)
    SearchLog.objects.create(
        filter_light=filter_light,
        filter_water=filter_water,
        filter_humidity=filter_humidity,
        category=filter_category
    )

    # 2. อัปเดตหรือสร้าง SearchSummary
    summary, created = SearchSummary.objects.get_or_create(
        filter_light=filter_light,
        filter_water=filter_water,
        filter_humidity=filter_humidity,
        category=filter_category
    )
    if not created:
        summary.search_count += 1
    else:
        summary.search_count = 1
    summary.save()

    # 3. auto gen FAQ ถ้าถึง threshold และยังไม่มี FAQ ผูกอยู่
    if summary.search_count >= FAQ_THRESHOLD and summary.faq is None:
        _auto_generate_faq(summary)


def _auto_generate_faq(summary: "SearchSummary"):
    """สร้าง FAQ อัตโนมัติจาก filter combo ใน summary โดยดึงรายชื่อพืชจริงมาใส่คำตอบ"""

    # --- สร้างข้อความเงื่อนไข (เฉพาะที่มีค่าจริง ไม่ใช่ None) ---
    parts = []
    if summary.filter_light:
        parts.append(f"แสง{LIGHT_LABELS.get(summary.filter_light, summary.filter_light)}")
    if summary.filter_water:
        parts.append(f"น้ำ{WATER_LABELS.get(summary.filter_water, summary.filter_water)}")
    if summary.filter_humidity:
        parts.append(f"ความชื้น{HUMIDITY_LABELS.get(summary.filter_humidity, summary.filter_humidity)}")
    if summary.category:
        parts.append(f"หมวด{summary.category.category_name}")

    condition_str = ", ".join(parts) if parts else "ทุกประเภท"

    # --- query พืชจริงที่ตรงกับเงื่อนไข ---
    plants = Plant.objects.all()
    if summary.filter_light:
        plants = plants.filter(light=summary.filter_light)
    if summary.filter_water:
        plants = plants.filter(water=summary.filter_water)
    if summary.filter_humidity:
        plants = plants.filter(humidity=summary.filter_humidity)
    if summary.category:
        plants = plants.filter(category=summary.category)

    answer = ", ".join(p.plant_name for p in plants) or "ยังไม่มีข้อมูลพืชที่ตรงกับเงื่อนไขนี้ในระบบ"

    faq = Faq.objects.create(
        title=f"พืชที่เหมาะกับ {condition_str}"[:50],  # ตัดไม่ให้เกิน max_length=50
        answer_text=f"พืชที่แนะนำ ได้แก่: {answer}",
    )

    summary.faq = faq
    summary.save()