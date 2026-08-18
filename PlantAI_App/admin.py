from django.contrib import admin
from .models import Admin, PlantCategory, Plant, Faq, SearchLog, SearchSummary

# Register your models here.

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('admin_id', 'username', 'email')
    search_fields = ('admin_id', 'username', 'email')


@admin.register(PlantCategory)
class PlantCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'category_name', 'detail', 'admin')
    search_fields = ('category_id', 'category_name')
    list_filter = ('admin',)


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ('plant_id', 'plant_name', 'category', 'light', 'water', 'humidity', 'admin')
    search_fields = ('plant_id', 'plant_name', 'description')
    list_filter = ('category', 'light', 'water', 'humidity', 'admin')


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = ('faq_id', 'title', 'created_at')
    search_fields = ('faq_id', 'title', 'answer_text')


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ('log_id', 'filter_light', 'filter_water', 'filter_humidity', 'category', 'searched_at')
    list_filter = ('category', 'searched_at')


@admin.register(SearchSummary)
class SearchSummaryAdmin(admin.ModelAdmin):
    list_display = ('summary_id', 'filter_light', 'filter_water', 'filter_humidity', 'category', 'search_count', 'faq', 'last_searched')
    list_filter = ('category', 'last_searched')