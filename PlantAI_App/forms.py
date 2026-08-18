from django import forms
from .models import Plant, PlantCategory, Faq, Admin

# ตัวเลือก Dropdown สำหรับ แสง, น้ำ, ความชื้น (ตรงกับค่าภาษาไทยในเล่ม)

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
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class PlantCategoryForm(forms.ModelForm):
    class Meta:
        model = PlantCategory
        fields = ['category_name', 'detail']
        labels = {
            'category_name': 'ชื่อหมวดหมู่พืช',
            'detail': 'รายละเอียดหมวดหมู่',
        }
        widgets = {
            'category_name': forms.TextInput(attrs={'class': 'form-control'}),
            'detail': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FaqForm(forms.ModelForm):
    class Meta:
        model = Faq
        fields = ['title', 'answer_text']
        labels = {
            'title': 'หัวข้อคำถาม',
            'answer_text': 'คำตอบ',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'answer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class AdminUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label="รหัสผ่าน (ปล่อยว่างถ้าไม่ต้องการเปลี่ยน)"
    )

    class Meta:
        model = Admin
        fields = ['username', 'email', 'password']
        labels = {
            'username': 'ชื่อผู้ใช้ (Username)',
            'email': 'อีเมล',
            'password': 'รหัสผ่าน',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class AdminLoginForm(forms.Form):
    username = forms.CharField(
        label='ชื่อผู้ใช้',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        label='รหัสผ่าน',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )