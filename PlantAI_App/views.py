import re
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
#  1. Map คีย์เวิร์ดภาษาไทย -> Value จริงใน Database ('low', 'medium', 'high')
# ─────────────────────────────────────────────
LIGHT_MAP = {
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

CATEGORY_SYNONYMS = {
    "ไม้คลุมดิน": ["คลุมดิน"],
    "ไม้ล้มลุก": ["ล้มลุก"],
    "ไม้พุ่ม": ["พุ่ม"],
    "ไม้ยืนต้น": ["ยืนต้น", "ต้นไม้ใหญ่"],
    "ไม้เลื้อย": ["เลื้อย", "ไม้เถา", "เถา"],
    "ไม้ประดับอื่น": ["ไม้ประดับ", "ประดับ", "อื่นๆ", "อื่น ๆ", "ทั่วไป"],
}


# ─────────────────────────────────────────────
#  2. Custom Decorator สำหรับตรวจสอบการเข้าสู่ระบบผู้ดูแลระบบ
# ─────────────────────────────────────────────
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'admin_id' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
#  2. RAG — ค้นหาข้อมูลพืชจาก DB ตามคำถามผู้ใช้
# ─────────────────────────────────────────────
def get_plant_context(user_input):
    plants = Plant.objects.select_related('category').all()
    user_input_lower = user_input.lower()
    user_input_clean = re.sub(r'[\sๆ]', '', user_input_lower)

    attr_query = Q()
    has_attr = False

    selected_light = None
    selected_water = None
    selected_humidity = None
    selected_category_obj = None

    # A. ตรวจหาแสง
    for db_val, keywords in LIGHT_MAP.items():
        if any(kw in user_input_lower for kw in keywords):
            attr_query &= Q(light=db_val)
            selected_light = db_val
            has_attr = True
            break

    # B. ตรวจหาน้ำ
    for db_val, keywords in WATER_MAP.items():
        if any(kw in user_input_lower for kw in keywords):
            attr_query &= Q(water=db_val)
            selected_water = db_val
            has_attr = True
            break

    # C. ตรวจหาความชื้น
    for db_val, keywords in HUMIDITY_MAP.items():
        if any(kw in user_input_lower for kw in keywords):
            attr_query &= Q(humidity=db_val)
            selected_humidity = db_val
            has_attr = True
            break

    # D. ตรวจหาหมวดหมู่
    matched_category_ids = set()
    db_categories = PlantCategory.objects.all()
    for cat in db_categories:
        if not cat.category_name:
            continue
        cat_name_clean = re.sub(r'[\sๆ]', '', cat.category_name.lower())
        
        if len(cat_name_clean) >= 2 and cat_name_clean in user_input_clean:
            matched_category_ids.add(cat.category_id)
            selected_category_obj = cat
            
        for syn_key, syn_words in CATEGORY_SYNONYMS.items():
            if syn_key in cat_name_clean and any(sw in user_input_lower for sw in syn_words):
                matched_category_ids.add(cat.category_id)
                selected_category_obj = cat

    if matched_category_ids:
        attr_query &= Q(category_id__in=list(matched_category_ids))
        has_attr = True

    # E. บันทึก SearchLog และ Query ฐานข้อมูล
    if has_attr:
        try:
            record_search(
                filter_light=selected_light,
                filter_water=selected_water,
                filter_humidity=selected_humidity,
                filter_category=selected_category_obj
            )
        except Exception as e:
            print(f"Record search log error: {e}")

        target_plants = plants.filter(attr_query).distinct()
    else:
        text_search = (
            Q(plant_name__icontains=user_input) |
            Q(description__icontains=user_input) |
            Q(category__category_name__icontains=user_input)
        )
        target_plants = plants.filter(text_search).distinct()

    if not target_plants.exists():
        return "ไม่พบข้อมูลต้นไม้ที่ตรงตามเงื่อนไขที่ระบุในฐานข้อมูล"

    # สร้างข้อความส่งให้ GPT (ใช้ get_FOO_display() เพื่อแปลง 'low' เป็น 'แสงน้อย' อัตโนมัติ)
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
คุณคือผู้ช่วยแนะนำต้นไม้ ตอบภาษาไทยอย่างเป็นกันเองและกระชับ

[ข้อมูลอ้างอิงจากฐานข้อมูล]
{context_data}

[กฎเหล็กในการตอบคำถาม - ต้องปฏิบัติตามอย่างเคร่งครัด]:
1. **ใช้อ้างอิงจากฐานข้อมูลเท่านั้น**: ห้ามคิดชื่อต้นไม้เอง ห้ามใช้ความรู้ภายนอกเด็ดขาด! ให้ใช้เฉพาะรายชื่อต้นไม้ที่ปรากฏอยู่ใน [ข้อมูลอ้างอิงจากฐานข้อมูล] ด้านบนเท่านั้น

2. **กรณีไม่พบข้อมูล**: หากข้อมูลอ้างอิงระบุว่า "ไม่พบข้อมูลต้นไม้..." ให้ตอบว่า:
   "ขออภัยครับ ไม่พบข้อมูลต้นไม้ที่ตรงตามเงื่อนไขในระบบครับ"

3. **กรณีพบข้อมูลต้นไม้**:
   - หากผู้ใช้พิมพ์ค้นหาด้วยคุณสมบัติ/หมวดหมู่สั้นๆ (เช่น "แสงน้อย", "น้ำปานกลาง", "ไม้ล้มลุก") ให้แสดงรายชื่อต้นไม้ที่มีในข้อมูลอ้างอิงออกมาเป็นข้อๆ (1., 2., 3., ...) โดยดึงชื่อจาก DB มาตรงๆ
   - หากผู้ใช้ขอคำแนะนำหรือระบุสถานที่ ให้เลือกต้นไม้จากข้อมูลอ้างอิงมา 1-2 ต้นพร้อมอธิบายสั้นๆ

4. **กรณีคำทักทาย**: หากพิมพ์แค่คำทักทาย ให้ตอบรับสุภาพและบอกว่าพร้อมแนะนำต้นไม้จากฐานข้อมูล
"""
                },
                {"role": "user", "content": user_input},
            ],
            temperature=0.2,  # ปรับ temperature ให้ต่ำลงเพื่อป้องกันโมเดลแต่งคำตอบเอง
        )

        return JsonResponse({'reply': completion.choices[0].message.content})

    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({'reply': 'ขออภัยครับ ระบบประมวลผลขัดข้อง'}, status=500)


# ─────────────────────────────────────────────
#  5. Authentication Views (Custom Session)
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
#  6. Management Views (Admin Scope)
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