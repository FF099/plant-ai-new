from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q
from openai import OpenAI

from .models import Admin, PlantCategory, Plant, Faq, SearchSummary, record_search
from .forms import PlantForm, PlantCategoryForm, FaqForm, AdminUserForm, AdminLoginForm

# เรียกใช้ OpenAI API Client
client = OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))


# ─────────────────────────────────────────────
#  Custom Decorator สำหรับตรวจสอบการเข้าสู่ระบบผู้ดูแลระบบ
# ─────────────────────────────────────────────
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'admin_id' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
#  RAG — ค้นหาข้อมูลพืชจาก DB ตามคำถามผู้ใช้
# ─────────────────────────────────────────────
def get_plant_context(user_input):
    plants = Plant.objects.select_related('category').all()
    user_input_lower = user_input.lower()

    attr_query = Q()
    has_attr = False

    # ตรวจหาคีย์เวิร์ดระดับแสง (ตรงกับฟิลด์ภาษาไทย)
    if any(k in user_input_lower for k in ["แสงน้อย", "ในร่ม"]):
        attr_query &= Q(light__icontains="แสงน้อย"); has_attr = True
    elif any(k in user_input_lower for k in ["แสงปานกลาง", "รำไร"]):
        attr_query &= Q(light__icontains="แสงปานกลาง"); has_attr = True
    elif any(k in user_input_lower for k in ["แสงแดดจ้า", "แสงมาก", "แดดจัด", "กลางแจ้ง"]):
        attr_query &= Q(light__icontains="แสงแดดจ้า"); has_attr = True

    # ตรวจหาคีย์เวิร์ดระดับน้ำ
    if "น้ำน้อย" in user_input_lower or "รดน้ำน้อย" in user_input_lower:
        attr_query &= Q(water__icontains="น้อย"); has_attr = True
    elif "น้ำปานกลาง" in user_input_lower or "รดน้ำปานกลาง" in user_input_lower:
        attr_query &= Q(water__icontains="ปานกลาง"); has_attr = True
    elif "น้ำมาก" in user_input_lower or "รดน้ำมาก" in user_input_lower:
        attr_query &= Q(water__icontains="มาก"); has_attr = True

    # ตรวจหาคีย์เวิร์ดระดับความชื้น
    if "ความชื้นต่ำ" in user_input_lower:
        attr_query &= Q(humidity__icontains="ต่ำ"); has_attr = True
    elif "ความชื้นปานกลาง" in user_input_lower:
        attr_query &= Q(humidity__icontains="ปานกลาง"); has_attr = True
    elif "ความชื้นสูง" in user_input_lower:
        attr_query &= Q(humidity__icontains="สูง"); has_attr = True

    if has_attr:
        target_plants = plants.filter(attr_query).distinct()[:10]
    else:
        text_search = (
            Q(plant_name__icontains=user_input) |
            Q(description__icontains=user_input) |
            Q(category__category_name__icontains=user_input)
        )
        target_plants = plants.filter(text_search).distinct()[:10]

    if not target_plants.exists():
        target_plants = plants.order_by('?')[:5]

    context = "ข้อมูลต้นไม้ที่ค้นพบ:\n"
    for p in target_plants:
        context += f"""
ชื่อ: {p.plant_name}
หมวดหมู่: {p.category.category_name}
รายละเอียดหมวดหมู่: {p.category.detail or "-"}
แสง: {p.light}
น้ำ: {p.water}
ความชื้น: {p.humidity}
รายละเอียด: {p.description or "-"}
-------------------
"""
    return context


# ─────────────────────────────────────────────
#  Public Views
# ─────────────────────────────────────────────
def index(request):
    plants = Plant.objects.all()
    categories = PlantCategory.objects.all()

    category_id = request.GET.get('category') or ''
    light = request.GET.get('light') or ''
    water = request.GET.get('water') or ''
    humidity = request.GET.get('humidity') or ''
    search = request.GET.get('search') or ''

    if category_id:
        plants = plants.filter(category_id=category_id)
    if light:
        plants = plants.filter(light=light)
    if water:
        plants = plants.filter(water=water)
    if humidity:
        plants = plants.filter(humidity=humidity)
    if search:
        plants = plants.filter(plant_name__icontains=search)

    # บันทึก Search Log + สร้าง FAQ อัตโนมัติเมื่อมีการค้นหา
    if any([light, water, humidity, category_id]):
        category_obj = PlantCategory.objects.filter(category_id=category_id).first() if category_id else None
        record_search(
            filter_light=light or None,
            filter_water=water or None,
            filter_humidity=humidity or None,
            filter_category=category_obj,
        )

    # Pagination
    paginator = Paginator(plants.order_by('plant_id'), 9)
    plants_page = paginator.get_page(request.GET.get('page'))

    # FAQ เรียงตามจำนวนการค้นหาสูงสุด
    popular_faqs = (
        SearchSummary.objects
        .filter(faq__isnull=False)
        .select_related('faq')
        .order_by('-search_count')[:5]
    )

    return render(request, "index.html", {
        "plants": plants_page,
        "categories": categories,
        "popular_faqs": popular_faqs,
        "selected_category": category_id,
        "selected_light": light,
        "selected_water": water,
        "selected_humidity": humidity,
        "search": search,
    })


def chat(request):
    return render(request, "chat.html")


@csrf_exempt
def chat_with_llm(request):
    if request.method != 'POST':
        return JsonResponse({'reply': 'Method not allowed'}, status=405)

    user_input = request.POST.get('message', '')

    try:
        context_data = get_plant_context(user_input)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""
                    คุณคือผู้เชี่ยวชาญด้านต้นไม้ ตอบภาษาไทยเท่านั้น

                    ใช้ข้อมูลจากฐานข้อมูลนี้เท่านั้น:
                    {context_data}

                    กติกาการตอบ:

                    1. ถ้าเป็นคำทักทายหรือสอบถามทั่วไป (เช่น สวัสดี, เป็นยังไงบ้าง):
                    - ตอบสั้น ๆ สุภาพ และแจ้งว่าช่วยแนะนำเรื่องต้นไม้ได้

                    2. ถ้าคำถามเกี่ยวข้องกับต้นไม้ (ทางตรง/ทางอ้อม เช่น พูดถึงแสง, น้ำ, ความชื้น, ชื่อพันธุ์, หมวดหมู่):
                    - ให้ใช้เฉพาะ "ข้อมูลต้นไม้ที่ค้นพบ" ด้านบนเท่านั้น ห้ามอ้างอิงต้นไม้ที่ไม่มีในลิสต์
                    - ถ้าถามหาต้นไม้ตามคุณสมบัติ (เช่น "ต้นไม้แสงมาก", "ขอรายชื่อ...") → ตอบเป็น "รายชื่อ" เท่านั้น ไม่ต้องอธิบายทีละต้น เช่น "ต้นไม้ที่เหมาะกับแสงมาก ได้แก่: A, B, C"
                    - ถ้าถามชื่อต้นไม้เจาะจง หรือขอคำแนะนำทั่วไป → แนะนำ 1 ชนิดพร้อมเหตุผลสั้นๆ
                    - ถ้าระบุจำนวน → ตอบตามจำนวนที่ขอ

                    การตอบ:
                    - พื้นฐาน → แนะนำ 1 ชนิดที่เหมาะที่สุด: "แนะนำเป็น '[ชื่อ]' เพราะ [เหตุผลสั้น ๆ]"
                    - ถ้าผู้ใช้ระบุจำนวน เช่น "ขอ 3 ชนิด", "สัก 5 ต้น" → ตอบตามจำนวนที่ขอ
                    - ถ้าขอเฉพาะชื่อ → ตอบเฉพาะชื่อ ไม่ต้องอธิบาย

                    3. ถ้าไม่เกี่ยวกับต้นไม้เลย:
                    - ตอบว่า "ขออภัย ระบบนี้แนะนำเฉพาะต้นไม้เท่านั้น"
                    """,
                },
                {"role": "user", "content": user_input},
            ],
        )

        return JsonResponse({'reply': completion.choices[0].message.content})

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({'reply': 'ขออภัยครับ ระบบประมวลผลขัดข้อง'}, status=500)


# ─────────────────────────────────────────────
#  Authentication Views (Custom Session)
# ─────────────────────────────────────────────
def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            admin_user = Admin.objects.filter(username=username, password=password).first()
            if admin_user:
                request.session['admin_id'] = admin_user.admin_id
                request.session['admin_username'] = admin_user.username
                return redirect('management')
            else:
                error_message = "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
    else:
        form = AdminLoginForm()

    return render(request, 'login.html', {'form': form, 'error': error_message})


def logout_view(request):
    request.session.flush()
    return redirect('/')


# ─────────────────────────────────────────────
#  Management Views (Admin Scope)
# ─────────────────────────────────────────────
@admin_required
def management_view(request):
    tab = request.GET.get('tab', 'plants')
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
    current_admin = get_object_or_404(Admin, admin_id=request.session['admin_id'])
    if request.method == 'POST':
        form = PlantForm(request.POST)
        if form.is_valid():
            plant = form.save(commit=False)
            plant.admin = current_admin
            plant.save()
            return redirect('/management/?tab=plants')
    else:
        form = PlantForm()
    return render(request, 'plant_form.html', {'form': form, 'title': 'เพิ่มข้อมูลพืช'})


@admin_required
def plant_edit(request, pk):
    plant = get_object_or_404(Plant, pk=pk)
    if request.method == 'POST':
        form = PlantForm(request.POST, instance=plant)
        if form.is_valid():
            form.save()
            return redirect('/management/?tab=plants')
    else:
        form = PlantForm(instance=plant)
    return render(request, 'plant_form.html', {'form': form, 'title': 'แก้ไขข้อมูลพืช'})


@admin_required
def plant_delete(request, pk):
    plant = get_object_or_404(Plant, pk=pk)
    plant.delete()
    return redirect('/management/?tab=plants')


@admin_required
def category_add(request):
    current_admin = get_object_or_404(Admin, admin_id=request.session['admin_id'])
    if request.method == 'POST':
        form = PlantCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.admin = current_admin
            cat.save()
            return redirect('/management/?tab=categories')
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
            return redirect('/management/?tab=categories')
    else:
        form = PlantCategoryForm(instance=cat)
    return render(request, 'category_form.html', {'form': form, 'title': 'แก้ไขหมวดหมู่พืช'})


@admin_required
def category_delete(request, pk):
    cat = get_object_or_404(PlantCategory, pk=pk)
    cat.delete()
    return redirect('/management/?tab=categories')


@admin_required
def faq_delete(request, pk):
    faq = get_object_or_404(Faq, pk=pk)
    faq.delete()
    return redirect('/management/?tab=faqs')


@admin_required
def admin_add(request):
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/management/?tab=admins')
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
            return redirect('/management/?tab=admins')
    else:
        form = AdminUserForm(instance=admin_obj)
    return render(request, 'admin_form.html', {'form': form, 'title': 'แก้ไขข้อมูลผู้ดูแลระบบ'})
