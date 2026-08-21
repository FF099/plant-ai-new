from django import forms
from .models import Plant, PlantCategory, Faq, Admin

# ตัวเลือก Dropdown สำหรับ แสง, น้ำ, ความชื้น (ตรงกับค่าภาษาไทยในเล่ม)


# ═════════════════════════════════════════════
# ฟอร์มสำหรับเพิ่ม/แก้ไขข้อมูลพืช (ผูกกับ model Plant)
# ═════════════════════════════════════════════
class PlantForm(forms.ModelForm):
    class Meta:
        model = Plant  # ผูกฟอร์มนี้กับโมเดล Plant
        # ระบุเฉพาะฟิลด์ที่ต้องการให้แสดงในฟอร์ม (plant_id ไม่ต้องใส่ เพราะ gen อัตโนมัติ)
        fields = ['plant_name', 'category', 'light', 'water', 'humidity', 'description']
        # ข้อความ label ภาษาไทยที่จะแสดงหน้าแต่ละช่องกรอกในฟอร์ม
        labels = {
            'plant_name': 'ชื่อพืช',
            'category': 'หมวดหมู่พืช',
            'light': 'ระดับแสง',
            'water': 'ระดับน้ำ',
            'humidity': 'ระดับความชื้น',
            'description': 'รายละเอียด',
        }
        # กำหนด widget (element HTML) และ class CSS (Bootstrap) ให้แต่ละฟิลด์
        widgets = {
            'plant_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),  # dropdown เลือกหมวดหมู่
            'light': forms.Select(attrs={'class': 'form-select'}),     # dropdown เลือกระดับแสง (จาก choices ใน model)
            'water': forms.Select(attrs={'class': 'form-select'}),     # dropdown เลือกระดับน้ำ
            'humidity': forms.Select(attrs={'class': 'form-select'}),  # dropdown เลือกระดับความชื้น
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),  # กล่องข้อความหลายบรรทัด
        }


# ═════════════════════════════════════════════
# ฟอร์มสำหรับเพิ่ม/แก้ไขหมวดหมู่พืช (ผูกกับ model PlantCategory)
# ═════════════════════════════════════════════
class PlantCategoryForm(forms.ModelForm):
    class Meta:
        model = PlantCategory
        # category_id ไม่ต้องใส่เพราะ gen อัตโนมัติ, admin จะถูกกำหนดใน view ไม่ใช่จากฟอร์ม
        fields = ['category_name', 'detail']
        labels = {
            'category_name': 'ชื่อหมวดหมู่พืช',
            'detail': 'รายละเอียดหมวดหมู่',
        }
        widgets = {
            'category_name': forms.TextInput(attrs={'class': 'form-control'}),
            'detail': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ═════════════════════════════════════════════
# ฟอร์มสำหรับเพิ่ม/แก้ไข FAQ ที่ admin สร้างเอง (ผูกกับ model Faq)
# ═════════════════════════════════════════════
class FaqForm(forms.ModelForm):
    class Meta:
        model = Faq
        # faq_id และ created_at ไม่ต้องใส่ เพราะถูกกำหนดค่าอัตโนมัติ (gen รหัส / auto_now_add)
        fields = ['title', 'answer_text']
        labels = {
            'title': 'หัวข้อคำถาม',
            'answer_text': 'คำตอบ',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'answer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


# ═════════════════════════════════════════════
# ฟอร์มสำหรับเพิ่ม/แก้ไขผู้ดูแลระบบ (ผูกกับ model Admin)
# ═════════════════════════════════════════════
class AdminUserForm(forms.ModelForm):
    # ฟิลด์ password แยกออกมานอกเหนือจาก Meta เพื่อกำหนดพฤติกรรมพิเศษ:
    # - required=False: เวลาแก้ไขข้อมูล admin เดิม จะปล่อยว่างได้ถ้าไม่ต้องการเปลี่ยนรหัสผ่าน
    # - PasswordInput: แสดงเป็นช่องกรอกแบบซ่อนตัวอักษร (••••)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label="รหัสผ่าน (ปล่อยว่างถ้าไม่ต้องการเปลี่ยน)"
    )

    class Meta:
        model = Admin
        # admin_id ไม่ต้องใส่เพราะ gen อัตโนมัติ
        fields = ['username', 'email', 'password']
        labels = {
            'username': 'ชื่อผู้ใช้ (Username)',
            'email': 'อีเมล',
            'password': 'รหัสผ่าน',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            # หมายเหตุ: ไม่ได้กำหนด widget ของ 'password' ไว้ที่นี่ เพราะถูกกำหนดไว้แล้วด้านบน
            # (การประกาศ field แยกนอก Meta จะ override ค่าที่มาจาก ModelForm อัตโนมัติ)
        }


# ═════════════════════════════════════════════
# ฟอร์มสำหรับหน้า Login ของผู้ดูแลระบบ (เป็น forms.Form ธรรมดา ไม่ผูกกับ model โดยตรง)
# ใช้ตรวจสอบรูปแบบข้อมูล (validation) ก่อนเอาไปเทียบกับข้อมูลจริงใน Admin model ที่ view
# ═════════════════════════════════════════════
class AdminLoginForm(forms.Form):
    username = forms.CharField(
        label='ชื่อผู้ใช้',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        label='รหัสผ่าน',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )