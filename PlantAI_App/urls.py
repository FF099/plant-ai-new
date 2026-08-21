from django.urls import path
from . import views

# รายการเส้นทาง (URL) ทั้งหมดของแอปนี้ แต่ละ path() จะจับคู่ URL pattern -> view function
# name='...' คือชื่อที่ใช้อ้างอิงใน template (เช่น {% url 'plant_add' %}) และใน redirect('name')
urlpatterns = [
    # หน้าแรก และ Chat AI
    path('', views.index, name='index'),                     # หน้าแรก แสดงรายการพืชทั้งหมด + filter
    path('chat/', views.chat, name='chat'),                   # หน้าแชทกับ AI (แสดง template chat.html)
    path('chat/api/', views.chat_with_llm, name='chat_api'),  # endpoint รับข้อความจากผู้ใช้ ส่งต่อให้ LLM แล้วตอบกลับเป็น JSON

    # ระบบสิทธิ์เข้าใช้งาน / ออกจากระบบ
    path('login/', views.login_view, name='login'),               # หน้า login สำหรับผู้ดูแลระบบ
    path('logout/', views.logout_view, name='logout'),            # ออกจากระบบ (ล้าง session)
    path('management/', views.management_view, name='management'),  # หน้าจัดการข้อมูลหลัก (ต้อง login ก่อน)

    # จัดการข้อมูลต้นไม้ (ใช้ <str:pk> รองรับรหัส P001, P002)
    path('management/plant/add/', views.plant_add, name='plant_add'),               # เพิ่มพืชใหม่
    path('management/plant/edit/<str:pk>/', views.plant_edit, name='plant_edit'),   # แก้ไขพืชตามรหัส pk (เช่น P001)
    path('management/plant/delete/<str:pk>/', views.plant_delete, name='plant_delete'),  # ลบพืชตามรหัส pk

    # จัดการประเภทต้นไม้ (ใช้ <str:pk> รองรับรหัส C001, C002)
    path('management/category/add/', views.category_add, name='category_add'),                 # เพิ่มหมวดหมู่ใหม่
    path('management/category/edit/<str:pk>/', views.category_edit, name='category_edit'),      # แก้ไขหมวดหมู่ตามรหัส pk
    path('management/category/delete/<str:pk>/', views.category_delete, name='category_delete'),  # ลบหมวดหมู่ตามรหัส pk

    # จัดการ FAQ (ใช้ <str:pk> รองรับรหัส F001, F002)
    path('management/faq/delete/<str:pk>/', views.faq_delete, name='faq_delete'),  # ลบ FAQ ตามรหัส pk (ไม่มีหน้า add/edit เพราะ FAQ ส่วนใหญ่ถูกสร้างอัตโนมัติ)

    # จัดการผู้ดูแลระบบ (ใช้ <str:pk> รองรับรหัส A001, A002)
    path('management/admin/add/', views.admin_add, name='admin_add'),             # เพิ่มผู้ดูแลระบบใหม่
    path('management/admin/edit/<str:pk>/', views.admin_edit, name='admin_edit'),  # แก้ไขข้อมูลผู้ดูแลระบบตามรหัส pk
]