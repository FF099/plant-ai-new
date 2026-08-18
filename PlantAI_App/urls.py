from django.urls import path
from . import views

urlpatterns = [
    # หน้าแรก และ Chat AI
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('chat/api/', views.chat_with_llm, name='chat_api'),

    # ระบบสิทธิ์เข้าใช้งาน / ออกจากระบบ
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('management/', views.management_view, name='management'),

    # จัดการข้อมูลต้นไม้ (ใช้ <str:pk> รองรับรหัส P001, P002)
    path('management/plant/add/', views.plant_add, name='plant_add'),
    path('management/plant/edit/<str:pk>/', views.plant_edit, name='plant_edit'),
    path('management/plant/delete/<str:pk>/', views.plant_delete, name='plant_delete'),

    # จัดการประเภทต้นไม้ (ใช้ <str:pk> รองรับรหัส C001, C002)
    path('management/category/add/', views.category_add, name='category_add'),
    path('management/category/edit/<str:pk>/', views.category_edit, name='category_edit'),
    path('management/category/delete/<str:pk>/', views.category_delete, name='category_delete'),

    # จัดการ FAQ (ใช้ <str:pk> รองรับรหัส F001, F002)
    path('management/faq/delete/<str:pk>/', views.faq_delete, name='faq_delete'),

    # จัดการผู้ดูแลระบบ (ใช้ <str:pk> รองรับรหัส A001, A002)
    path('management/admin/add/', views.admin_add, name='admin_add'),
    path('management/admin/edit/<str:pk>/', views.admin_edit, name='admin_edit'),
]
