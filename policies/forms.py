from django import forms
from django.core.exceptions import ValidationError
from .models import InsurancePolicy, Installment, Payment, GuaranteeCheck, Endorsement
import jdatetime


class ExcelUploadForm(forms.Form):
    """Form for uploading Excel file"""
    excel_file = forms.FileField(
        label='فایل اکسل گزارش بیمه',
        help_text='فایل با پسوند .xlsx از نرم‌افزار فروش بیمه',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx'
        })
    )

    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']
        if not file.name.endswith('.xlsx'):
            raise ValidationError('فقط فایل‌های .xlsx مجاز هستند')
        if file.size > 50 * 1024 * 1024:  # 50MB
            raise ValidationError('حجم فایل نباید بیشتر از ۵۰ مگابایت باشد')
        return file


class InstallmentGenerateForm(forms.Form):
    """Form to auto-generate installments for a policy"""
    INTERVAL_CHOICES = [
        ('30', 'ماهانه (هر ۳۰ روز)'),
        ('60', 'دو ماهه (هر ۶۰ روز)'),
    ]

    down_payment_amount = forms.IntegerField(
        label='مبلغ پیش پرداخت (ریال)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'dir': 'ltr', 'id': 'id_down_payment'
        })
    )
    count = forms.IntegerField(
        label='تعداد اقساط',
        min_value=1,
        max_value=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'dir': 'ltr', 'id': 'id_installment_count'
        })
    )
    amount_per_installment = forms.IntegerField(
        label='مبلغ هر قسط (ریال)',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'dir': 'ltr', 'id': 'id_amount_per_installment'
        })
    )
    start_date = forms.CharField(
        label='تاریخ شروع اقساط',
        max_length=20,
        help_text='فرمت: 1405/05/01',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'dir': 'ltr', 'placeholder': '1405/05/01'
        })
    )
    interval = forms.ChoiceField(
        label='فاصله اقساط',
        choices=INTERVAL_CHOICES,
        initial='30',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_start_date(self):
        date = self.cleaned_data['start_date']
        try:
            parts = date.split('/')
            jdatetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            raise ValidationError('تاریخ نامعتبر است. فرمت صحیح: 1405/05/01')
        return date


class PaymentForm(forms.ModelForm):
    """Form for recording a payment"""

    class Meta:
        model = Payment
        fields = ['installment', 'amount', 'payment_date', 'payment_method',
                  'reference_number', 'check_due_date', 'check_bank_name', 'check_status', 'notes']
        widgets = {
            'installment': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 'dir': 'ltr',
                'placeholder': 'مبلغ به ریال'
            }),
            'payment_date': forms.TextInput(attrs={
                'class': 'form-control', 'dir': 'ltr',
                'placeholder': '1405/05/01'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control', 'dir': 'ltr'
            }),
            'check_due_date': forms.TextInput(attrs={
                'class': 'form-control date-input', 'dir': 'ltr',
                'placeholder': '1405/04/29'
            }),
            'check_bank_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'check_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
        }
        labels = {
            'installment': 'قسط مربوطه',
            'amount': 'مبلغ واریزی (ریال)',
            'payment_date': 'تاریخ واریز',
            'payment_method': 'روش پرداخت',
            'reference_number': 'شماره چک / پیگیری',
            'check_due_date': 'تاریخ سررسید چک',
            'check_bank_name': 'نام بانک',
            'check_status': 'وضعیت چک',
            'notes': 'توضیحات',
        }

    def __init__(self, *args, **kwargs):
        policy_id = kwargs.pop('policy_id', None)
        super().__init__(*args, **kwargs)
        if policy_id:
            self.fields['installment'].queryset = Installment.objects.filter(
                policy_id=policy_id
            )
            self.fields['installment'].required = False
            self.fields['installment'].empty_label = 'ثبت بدون انتخاب قسط'

    def clean_payment_date(self):
        date = self.cleaned_data['payment_date']
        # Normalize date: remove extra slashes and format correctly
        date = date.replace(' ', '')
        if date and '/' not in date and len(date) == 8:
            date = f'{date[:4]}/{date[4:6]}/{date[6:8]}'
        try:
            parts = date.split('/')
            if len(parts) != 3:
                raise ValidationError('فرمت تاریخ صحیح نیست. فرمت: 1405/05/01')
            jdatetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            raise ValidationError('تاریخ نامعتبر است. فرمت صحیح: 1405/05/01')
        return date

    def clean_reference_number(self):
        ref = self.cleaned_data.get('reference_number')
        if ref:
            ref = ref.strip()
            # Convert empty string to None (NULL) to avoid UNIQUE constraint issues
            if not ref:
                return None
            # Check uniqueness (exclude current instance if editing)
            qs = Payment.objects.filter(reference_number=ref)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f'شماره پیگیری "{ref}" قبلاً ثبت شده است. شماره پیگیری باید یکتا باشد.'
                )
        return ref if ref else None


class PolicyEditForm(forms.ModelForm):
    """Form for editing policy information"""

    class Meta:
        model = InsurancePolicy
        fields = [
            'insurance_type', 'policyholder', 'phone', 'national_code', 'address',
            'policy_number', 'plate_number', 'vehicle_type', 'vehicle_year',
            'start_date', 'end_date', 'issue_date', 'duration_days',
            'total_premium', 'total_with_tax', 'vat',
            'body_coverage', 'financial_coverage', 'vehicle_value',
            'down_payment',
            'agent_name', 'contract_description', 'status',
        ]
        widgets = {
            'insurance_type': forms.Select(attrs={'class': 'form-select'}),
            'policyholder': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 'dir': 'ltr', 'placeholder': '09121234567'
            }),
            'national_code': forms.TextInput(attrs={
                'class': 'form-control', 'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
            'policy_number': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'plate_number': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_year': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'start_date': forms.TextInput(attrs={
                'class': 'form-control date-input', 'dir': 'ltr', 'placeholder': '1405/04/29'
            }),
            'end_date': forms.TextInput(attrs={
                'class': 'form-control date-input', 'dir': 'ltr', 'placeholder': '1406/04/29'
            }),
            'issue_date': forms.TextInput(attrs={
                'class': 'form-control date-input', 'dir': 'ltr', 'placeholder': '1405/04/29'
            }),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'total_premium': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'total_with_tax': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'vat': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'body_coverage': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'financial_coverage': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'vehicle_value': forms.NumberInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'down_payment': forms.NumberInput(attrs={
                'class': 'form-control', 'dir': 'ltr',
                'placeholder': 'مبلغ پیش پرداخت به ریال'
            }),
            'agent_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_description': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'policyholder': 'نام بیمه گذار',
            'phone': 'شماره تماس',
            'national_code': 'کد ملی',
            'address': 'نشانی',
            'policy_number': 'شماره بیمه نامه',
            'plate_number': 'شماره پلاک',
            'vehicle_type': 'نوع خودرو',
            'vehicle_year': 'سال ساخت',
            'start_date': 'تاریخ شروع',
            'end_date': 'تاریخ انقضاء',
            'issue_date': 'تاریخ صدور',
            'duration_days': 'مدت (روز)',
            'total_premium': 'کل حق بیمه (ریال)',
            'total_with_tax': 'حق بیمه با مالیات (ریال)',
            'vat': 'مالیات ارزش افزوده',
            'body_coverage': 'پوشش بدنی (میلیون ریال)',
            'financial_coverage': 'پوشش مالی (میلیون ریال)',
            'vehicle_value': 'ارزش وسیله نقلیه (ریال)',
            'down_payment': 'پیش پرداخت (ریال)',
            'agent_name': 'نماینده / معرف',
            'contract_description': 'شرح قرارداد',
            'status': 'وضعیت',
        }

    def clean_start_date(self):
        return self._normalize_date(self.cleaned_data.get('start_date'))

    def clean_end_date(self):
        return self._normalize_date(self.cleaned_data.get('end_date'))

    def clean_issue_date(self):
        return self._normalize_date(self.cleaned_data.get('issue_date'))

    def _normalize_date(self, date):
        if not date:
            return date
        date = date.replace(' ', '')
        if '/' not in date and len(date) == 8:
            date = f'{date[:4]}/{date[4:6]}/{date[6:8]}'
        return date


class InstallmentEditForm(forms.ModelForm):
    """Form for editing a single installment"""

    class Meta:
        model = Installment
        fields = ['amount', 'due_date', 'status', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 'dir': 'ltr'
            }),
            'due_date': forms.TextInput(attrs={
                'class': 'form-control', 'dir': 'ltr',
                'placeholder': '1405/05/01'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
        }
        labels = {
            'amount': 'مبلغ قسط (ریال)',
            'due_date': 'تاریخ سررسید',
            'status': 'وضعیت',
            'notes': 'توضیحات',
        }


class GuaranteeCheckForm(forms.ModelForm):
    """Form for adding a guarantee check"""

    class Meta:
        model = GuaranteeCheck
        fields = ['check_number', 'bank_name', 'amount', 'due_date', 'notes']
        widgets = {
            'check_number': forms.TextInput(attrs={
                'class': 'form-control', 'dir': 'ltr'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 'dir': 'ltr', 'placeholder': 'مبلغ به ریال'
            }),
            'due_date': forms.TextInput(attrs={
                'class': 'form-control date-input', 'dir': 'ltr', 'placeholder': '1405/04/29'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
        }
        labels = {
            'check_number': 'شماره چک',
            'bank_name': 'نام بانک',
            'amount': 'مبلغ چک (ریال)',
            'due_date': 'تاریخ سررسید',
            'notes': 'توضیحات',
        }


class EndorsementForm(forms.ModelForm):
    """Form for adding an endorsement (الحاقیه)"""

    class Meta:
        model = Endorsement
        fields = ['amount', 'reason', 'date']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 'dir': 'ltr', 'placeholder': 'مبلغ اضافه شده به ریال'
            }),
            'reason': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'مثال: تغییر دیه سال ۱۴۰۵'
            }),
            'date': forms.TextInput(attrs={
                'class': 'form-control date-input', 'dir': 'ltr', 'placeholder': '1405/04/29'
            }),
        }
        labels = {
            'amount': 'مبلغ الحاقیه (ریال)',
            'reason': 'دلیل الحاقیه',
            'date': 'تاریخ ثبت',
        }
