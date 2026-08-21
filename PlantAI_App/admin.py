from django.contrib import admin
from .models import Admin, PlantCategory, Plant, Faq, SearchLog, SearchSummary

# Register your models here.
# ลงทะเบียนแต่ละ model กับ Django Admin เพื่อให้จัดการข้อมูลผ่านหน้า /admin ได้


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('admin_id', 'username', 'email')  # คอลัมน์ที่แสดงในตารางรายการ
    search_fields = ('admin_id', 'username', 'email')  # ช่องค้นหาด้านบน ค้นได้จากฟิลด์เหล่านี้


@admin.register(PlantCategory)
class PlantCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name', 'detail', 'admin')
    search_fields = ('category_id', 'category_name')
    list_filter = ('admin',)  # กรองรายการตาม admin ผู้สร้างได้จากแถบด้านขวา


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ('plant_id', 'plant_name', 'category', 'light', 'water', 'humidity', 'admin')
    search_fields = ('plant_id', 'plant_name', 'description')
    # กรองรายการพืชตามหมวดหมู่/แสง/น้ำ/ความชื้น/ผู้ดูแล
    list_filter = ('category', 'light', 'water', 'humidity', 'admin')


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = ('faq_id', 'title', 'created_at')
    search_fields = ('faq_id', 'title', 'answer_text')


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    # log ดิบของการค้นหาแต่ละครั้ง ไม่มี search_fields เพราะเน้นดู/กรองมากกว่าค้นหาข้อความ
    list_display = ('log_id', 'filter_light', 'filter_water', 'filter_humidity', 'category', 'searched_at')
    list_filter = ('category', 'searched_at')


@admin.register(SearchSummary)
class SearchSummaryAdmin(admin.ModelAdmin):
    # สรุปยอดการค้นหาต่อ filter combo หนึ่งๆ พร้อม FAQ ที่ถูก auto-gen (ถ้ามี)
    list_display = ('summary_id', 'filter_light', 'filter_water', 'filter_humidity', 'category', 'search_count', 'faq', 'last_searched')
    list_filter = ('category', 'last_searched')