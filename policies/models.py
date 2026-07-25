import jdatetime
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def today_jalali():
    """Return today's jalali date as string 'YYYY/MM/DD'"""
    return jdatetime.date.today().strftime('%Y/%m/%d')


class InsuranceType(models.Model):
    """Insurance product type"""
    name = models.CharField('نام نوع بیمه', max_length=100)
    slug = models.SlugField('شناسه', max_length=100, unique=True, blank=True)
    description = models.TextField('توضیحات', blank=True, null=True)
    is_active = models.BooleanField('فعال', default=True)
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        verbose_name = 'نوع بیمه'
        verbose_name_plural = 'انواع بیمه'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class InsurancePolicy(models.Model):
    """Insurance policy information imported from Excel"""

    # Core fields from Excel
    policy_code = models.CharField(
        'کد رایانه بیمه نامه', max_length=50, unique=True, blank=True, null=True
    )
    insurance_type = models.ForeignKey(
        InsuranceType, on_delete=models.SET_NULL,
        related_name='policies', verbose_name='نوع بیمه',
        blank=True, null=True
    )
    policy_number = models.CharField(
        'شماره بیمه نامه', max_length=100, blank=True, null=True
    )
    policyholder = models.CharField('بیمه گذار', max_length=255)
    contract_number = models.TextField('شماره قرارداد', blank=True, null=True)
    contract_description = models.CharField(
        'شرح قرارداد', max_length=500, blank=True, null=True
    )
    status = models.CharField('وضعیت', max_length=100, blank=True, null=True)

    # Dates
    start_date = models.CharField(
        'تاریخ شروع', max_length=20, blank=True, null=True,
        help_text="فرمت: 1405/04/29"
    )
    end_date = models.CharField(
        'تاریخ انقضاء', max_length=20, blank=True, null=True,
        help_text="فرمت: 1405/04/29"
    )
    issue_date = models.CharField(
        'تاریخ صدور', max_length=20, blank=True, null=True,
        help_text="فرمت: 1405/04/29"
    )
    duration_days = models.IntegerField('مدت (روز)', blank=True, null=True)

    # Financial
    total_premium = models.BigIntegerField('کل حق بیمه (ریال)', blank=True, null=True)
    vat = models.BigIntegerField('مالیات ارزش افزوده', blank=True, null=True)
    total_with_tax = models.BigIntegerField(
        'حق بیمه با مالیات و عوارض (ریال)', blank=True, null=True
    )

    # Vehicle info
    plate_number = models.CharField(
        'شماره پلاک', max_length=100, blank=True, null=True
    )
    vehicle_type = models.CharField(
        'نوع وسیله نقلیه', max_length=255, blank=True, null=True
    )
    vehicle_year = models.IntegerField('سال ساخت', blank=True, null=True)
    body_coverage = models.BigIntegerField(
        'پوشش بدنی (میلیون ریال)', blank=True, null=True
    )
    financial_coverage = models.BigIntegerField(
        'پوشش مالی (میلیون ریال)', blank=True, null=True
    )
    vehicle_value = models.BigIntegerField(
        'ارزش وسیله نقلیه (ریال)', blank=True, null=True,
        help_text='مخصوص بیمه بدنه'
    )

    # Agent info
    agent_name = models.CharField(
        'معرف / نماینده', max_length=255, blank=True, null=True
    )
    archive_number = models.CharField(
        'شماره بایگانی', max_length=100, blank=True, null=True
    )

    # Contact info (editable fields)
    phone = models.CharField(
        'شماره تماس', max_length=50, blank=True, null=True,
        help_text='مثال: 09121234567'
    )
    national_code = models.CharField(
        'کد ملی', max_length=20, blank=True, null=True
    )
    address = models.TextField(
        'نشانی', blank=True, null=True
    )

    # Down payment (پیش پرداخت)
    down_payment = models.BigIntegerField(
        'پیش پرداخت (ریال)', blank=True, null=True, default=0,
        help_text='مبلغ پیش پرداخت که از کل کسر و باقی‌مانده قسط‌بندی می‌شود'
    )
    down_payment_paid = models.BooleanField(
        'پیش پرداخت پرداخت شد؟', default=False
    )
    down_payment_date = models.CharField(
        'تاریخ پرداخت پیش پرداخت', max_length=20, blank=True, null=True,
        help_text="فرمت: 1405/04/29"
    )

    # Extra raw data (full Excel row as JSON)
    raw_data = models.JSONField('داده خام', blank=True, null=True)

    # Overpayment credit (instead of modifying installment amounts)
    overpayment_credit = models.BigIntegerField(
        'اعتبار اضافه پرداخت (ریال)', blank=True, null=True, default=0,
        help_text='اضافه پرداختی که به قسط بعدی اعمال می‌شود'
    )

    # Metadata
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)
    updated_at = models.DateTimeField('آخرین ویرایش', auto_now=True)

    class Meta:
        verbose_name = 'بیمه نامه'
        verbose_name_plural = 'بیمه نامه‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.policyholder} - {self.plate_number or 'بدون پلاک'}"

    @property
    def remaining_installments_count(self):
        """Number of unpaid installments"""
        return self.installments.filter(status='pending').count()

    @property
    def total_paid(self):
        """Total amount paid for this policy"""
        from django.db.models import Sum
        result = self.payments.aggregate(total=Sum('amount'))
        return result['total'] or 0

    @property
    def amount_after_downpayment(self):
        """Total amount minus down payment (amount to be split into installments)"""
        total = self.total_with_tax or 0
        dp = self.down_payment or 0
        return max(0, total - dp)

    @property
    def total_debt(self):
        """Total remaining debt"""
        total_installments = self.installments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        return total_installments - self.total_paid

    @property
    def overpayment_total(self):
        """Total overpayment credit available on this policy"""
        return self.overpayment_credit or 0


class Installment(models.Model):
    """Installment plan for each policy"""

    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('overdue', 'دیرکرد'),
        ('partial', 'پرداخت جزیی'),
    ]

    policy = models.ForeignKey(
        InsurancePolicy, on_delete=models.CASCADE,
        related_name='installments', verbose_name='بیمه نامه'
    )
    installment_number = models.IntegerField('شماره قسط')
    amount = models.BigIntegerField('مبلغ قسط (ریال)')
    due_date = models.CharField(
        'تاریخ سررسید', max_length=20,
        help_text="فرمت: 1405/04/29"
    )
    status = models.CharField(
        'وضعیت', max_length=20, choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField('توضیحات', blank=True, null=True)
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        verbose_name = 'قسط'
        verbose_name_plural = 'اقساط'
        ordering = ['policy', 'installment_number']
        unique_together = ['policy', 'installment_number']

    def __str__(self):
        return f"قسط {self.installment_number} - {self.policy.policyholder} - {self.amount:,} ریال"

    def save(self, *args, **kwargs):
        """Auto-update status based on due date"""
        if self.status == 'pending' and self.due_date:
            try:
                due = jdatetime.date(
                    int(self.due_date[:4]),
                    int(self.due_date[5:7]),
                    int(self.due_date[8:10])
                )
                if due < jdatetime.date.today():
                    self.status = 'overdue'
            except (ValueError, IndexError):
                pass
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment record for installments"""

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'نقدی'),
        ('card', 'کارت به کارت'),
        ('check', 'چک'),
        ('wire', 'حواله بانکی'),
        ('other', 'سایر'),
    ]

    installment = models.ForeignKey(
        Installment, on_delete=models.CASCADE,
        related_name='payments', verbose_name='قسط',
        blank=True, null=True
    )
    policy = models.ForeignKey(
        InsurancePolicy, on_delete=models.CASCADE,
        related_name='payments', verbose_name='بیمه نامه'
    )
    amount = models.BigIntegerField('مبلغ واریزی (ریال)')
    payment_date = models.CharField(
        'تاریخ واریز', max_length=20,
        help_text="فرمت: 1405/04/29"
    )
    payment_method = models.CharField(
        'روش پرداخت', max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    reference_number = models.CharField(
        'شماره پیگیری', max_length=100, blank=True, null=True, unique=True,
        help_text='شماره پیگیری یکتا - نمی‌تواند تکراری باشد'
    )
    notes = models.TextField('توضیحات', blank=True, null=True)

    # Cheque-specific fields
    check_due_date = models.CharField(
        'تاریخ سررسید چک', max_length=20, blank=True, null=True,
        help_text="فرمت: 1405/04/29"
    )
    check_bank_name = models.CharField(
        'نام بانک', max_length=200, blank=True, null=True
    )
    CHECK_STATUS_CHOICES = [
        ('pending', 'در انتظار وصول'),
        ('cleared', 'پاس شده'),
        ('returned', 'برگشت خورده'),
    ]
    check_status = models.CharField(
        'وضعیت چک', max_length=20, choices=CHECK_STATUS_CHOICES,
        blank=True, null=True, default=None,
        help_text='وضعیت وصول چک'
    )
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        verbose_name = 'واریزی'
        verbose_name_plural = 'واریزی‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"واریز {self.amount:,} ریال - {self.policy.policyholder}"
        )

    def save(self, *args, **kwargs):
        """Auto-update installment status and handle overpayment as credit"""
        from django.db import transaction

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # When cheque is marked as cleared, mark installment as paid
        if not is_new and self.payment_method == 'check' and self.check_status == 'cleared' and self.installment:
            self.installment.status = 'paid'
            self.installment.save(update_fields=['status'])
            return

        if is_new and self.installment:
            with transaction.atomic():
                total_paid = self.installment.payments.aggregate(
                    total=models.Sum('amount')
                )['total'] or 0

                # Check if there's available credit to apply
                credit = self.policy.overpayment_credit or 0
                effective_amount = max(0, self.installment.amount - credit)

                if total_paid >= effective_amount:
                    self.installment.status = 'paid'

                    # Handle overpayment → add to credit instead of modifying next installment
                    overpayment = total_paid - effective_amount
                    if overpayment > 0:
                        self.policy.overpayment_credit = (self.policy.overpayment_credit or 0) + overpayment
                        self.policy.save(update_fields=['overpayment_credit'])

                    # If credit was used, deduct it
                    if credit > 0 and total_paid > 0:
                        used_credit = min(credit, total_paid)
                        self.policy.overpayment_credit = (self.policy.overpayment_credit or 0) - used_credit
                        self.policy.save(update_fields=['overpayment_credit'])

                elif total_paid > 0:
                    self.installment.status = 'partial'
                else:
                    self.installment.status = 'pending'

                self.installment.save(update_fields=['status'])


class Endorsement(models.Model):
    """الحاقیه —增加 مبلغ بیمه به دلیل تغییر دیه و ..."""
    policy = models.ForeignKey(
        InsurancePolicy, on_delete=models.CASCADE,
        related_name='endorsements', verbose_name='بیمه نامه'
    )
    amount = models.BigIntegerField('مبلغ الحاقیه (ریال)')
    reason = models.CharField('دلیل الحاقیه', max_length=500,
                              default='تغییر دیه',
                              help_text='مثال: تغییر دیه سال ۱۴۰۵')
    date = models.CharField('تاریخ ثبت', max_length=20,
                            help_text="فرمت: 1405/04/29")
    previous_total = models.BigIntegerField('مبلغ کل قبل از الحاقیه')
    new_total = models.BigIntegerField('مبلغ کل بعد از الحاقیه')
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        verbose_name = 'الحاقیه'
        verbose_name_plural = 'الحاقیه‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'الحاقیه {self.amount:,} ریال - {self.reason[:30]}'

    def save(self, *args, **kwargs):
        """Auto-calculate totals and redistribute remaining installments"""
        from django.db import transaction

        is_new = self.pk is None
        with transaction.atomic():
            if is_new:
                # Record previous total
                self.previous_total = self.policy.total_with_tax or 0
                # Update policy total
                self.policy.total_with_tax = (self.policy.total_with_tax or 0) + self.amount
                self.new_total = self.policy.total_with_tax
                self.policy.save(update_fields=['total_with_tax'])

            super().save(*args, **kwargs)

            if is_new:
                # Redistribute the additional amount across unpaid installments
                self._redistribute_installments()

    def _redistribute_installments(self):
        """Add the endorsement amount proportionally to unpaid installments"""
        unpaid = self.policy.installments.filter(
            status__in=['pending', 'overdue', 'partial']
        ).order_by('installment_number')

        if not unpaid.exists():
            return

        additional_per_installment = self.amount // unpaid.count()
        remainder = self.amount - (additional_per_installment * unpaid.count())

        for i, inst in enumerate(unpaid):
            extra = additional_per_installment + (1 if i == 0 else 0)  # remainder goes to first
            inst.amount += extra
            note = f'[الحاقیه {self.reason}: +{extra:,} ریال]'
            old_notes = inst.notes or ''
            inst.notes = f'{note}\n{old_notes}' if old_notes else note
            inst.save(update_fields=['amount', 'notes'])


class GuaranteeCheck(models.Model):
    """Cheque received as guarantee for installment payment"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار وصول'),
        ('cleared', 'وصول شده'),
        ('returned', 'برگشت خورده'),
    ]

    policy = models.ForeignKey(
        InsurancePolicy, on_delete=models.CASCADE,
        related_name='guarantee_checks', verbose_name='بیمه نامه'
    )
    check_number = models.CharField(
        'شماره چک', max_length=100
    )
    bank_name = models.CharField(
        'نام بانک', max_length=200, blank=True, null=True
    )
    amount = models.BigIntegerField('مبلغ چک (ریال)')
    due_date = models.CharField(
        'تاریخ سررسید', max_length=20,
        help_text="فرمت: 1405/04/29"
    )
    status = models.CharField(
        'وضعیت', max_length=20, choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField('توضیحات', blank=True, null=True)
    created_at = models.DateTimeField('تاریخ ثبت', auto_now_add=True)

    class Meta:
        verbose_name = 'چک ضمانت'
        verbose_name_plural = 'چک‌های ضمانت'
        ordering = ['-created_at']

    def __str__(self):
        return f'چک {self.check_number} - {self.amount:,} ریال'
