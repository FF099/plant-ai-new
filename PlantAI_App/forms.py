from django import forms
from .models import Plant, PlantCategory, Faq, Admin

# ตัวเลือก Dropdown สำหรับ แสง, น้ำ, ความชื้น (ตรงกับค่าภาษาไทยในเล่ม)


# ═════════════════════════════════════════════
# ฟอร์มสำหรับเพิ่ม/แก้ไขข้อมูลพืช (ผูกกับ model Plant)
# ═════════════════════════════════════════════
class PlantForm(forms.ModelForm):
    class Meta:
        model = Plant
        fields = ['plant_name', 'category', 'light', 'water', 'humidity', 'description']

        labels = {
            'plant_name': 'ชื่อพืช',
            'category': 'หมวดหมู่พืช',
            'light': 'ระดับแสง',
            'water': 'ระดับน้ำ',
            'humidity': 'ระดับความชื้น',
            'description': 'รายละเอียด',
        }

        widgets = {
            'plant_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'light': forms.Select(attrs={'class': 'form-select'}),
            'water': forms.Select(attrs={'class': 'form-select'}),
            'humidity': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
        }

    def clean_plant_name(self):
        plant_name = self.cleaned_data['plant_name'].strip()

        # ตรวจว่าชื่อพืชซ้ำกับพืชหรือไม่
        plants = Plant.objects.filter(
            plant_name__iexact=plant_name
        )

        # ตอนแก้ไขข้อมูล ให้ไม่นับข้อมูลตัวเอง
        if self.instance.pk:
            plants = plants.exclude(pk=self.instance.pk)

        if plants.exists():
            raise forms.ValidationError(
                'ชื่อพืชนี้มีอยู่ในระบบแล้ว'
            )

        # ตรวจว่าชื่อพืชซ้ำกับชื่อหมวดหมู่หรือไม่
        categories = PlantCategory.objects.filter(
            category_name__iexact=plant_name
        )

        if categories.exists():
            raise forms.ValidationError(
                'ชื่อพืชนี้ซ้ำกับชื่อหมวดหมู่พืช'
            )

        return plant_name


# ═════════════════════════════════════════════
# ฟอร์มสำหรับเพิ่ม/แก้ไขหมวดหมู่พืช (ผูกกับ model PlantCategory)
# ═════════════════════════════════════════════
class PlantCategoryForm(forms.ModelForm):
    class Meta:
        model = PlantCategory
        fields = ['category_name', 'detail']

        labels = {
            'category_name': 'ชื่อหมวดหมู่พืช',
            'detail': 'รายละเอียดหมวดหมู่',
        }

        widgets = {
            'category_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'detail': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3
                }
            ),
        }

    def clean_category_name(self):
        category_name = self.cleaned_data['category_name'].strip()

        # ตรวจว่าชื่อหมวดหมู่ซ้ำกับหมวดหมู่หรือไม่
        categories = PlantCategory.objects.filter(
            category_name__iexact=category_name
        )

        # ตอนแก้ไขข้อมูล ให้ไม่นับข้อมูลตัวเอง
        if self.instance.pk:
            categories = categories.exclude(pk=self.instance.pk)

        if categories.exists():
            raise forms.ValidationError(
                'ชื่อหมวดหมู่นี้มีอยู่ในระบบแล้ว'
            )

        # ตรวจว่าชื่อหมวดหมู่ซ้ำกับชื่อพืชหรือไม่
        plants = Plant.objects.filter(
            plant_name__iexact=category_name
        )

        if plants.exists():
            raise forms.ValidationError(
                'ชื่อหมวดหมู่นี้ซ้ำกับชื่อพืช'
            )

        return category_name


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