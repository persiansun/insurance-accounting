from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import InsurancePolicy, Installment, Payment, InsuranceType, GuaranteeCheck, Endorsement, AppSettings


@admin.register(InsuranceType)
class InsuranceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'policy_count', 'is_active']
    search_fields = ['name']

    def policy_count(self, obj):
        return obj.policies.count()
    policy_count.short_description = 'تعداد بیمه نامه'


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'policy_code', 'policyholder_short', 'insurance_type_name',
        'plate_number',
        'total_with_tax_display', 'installments_status', 'created_at'
    ]
    list_filter = ['status', 'insurance_type', 'created_at', 'vehicle_type']
    search_fields = ['policyholder', 'plate_number', 'policy_code', 'policy_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 25

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'policy_code', 'policy_number', 'policyholder',
                'contract_description', 'status'
            )
        }),
        ('تاریخ‌ها', {
            'fields': ('start_date', 'end_date', 'issue_date', 'duration_days')
        }),
        ('اطلاعات مالی', {
            'fields': (
                'total_premium', 'vat', 'total_with_tax',
                'body_coverage', 'financial_coverage'
            )
        }),
        ('خودرو', {
            'fields': (
                'plate_number', 'vehicle_type', 'vehicle_year'
            )
        }),
        ('اطلاعات تکمیلی', {
            'fields': (
                'agent_name', 'agent_phone', 'introducer_name', 'introducer_phone',
                'archive_number', 'contract_number',
                'raw_data'
            )
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def policyholder_short(self, obj):
        name = obj.policyholder or ''
        return name[:40] + '...' if len(name) > 40 else name
    policyholder_short.short_description = 'بیمه گذار'
    policyholder_short.admin_order_field = 'policyholder'

    def insurance_type_name(self, obj):
        return obj.insurance_type.name if obj.insurance_type else '-'
    insurance_type_name.short_description = 'نوع بیمه'
    insurance_type_name.admin_order_field = 'insurance_type'

    def total_with_tax_display(self, obj):
        if obj.total_with_tax:
            return f'{obj.total_with_tax:,}'
        return '-'
    total_with_tax_display.short_description = 'مبلغ کل'

    def installments_status(self, obj):
        total = obj.installments.count()
        paid = obj.installments.filter(status='paid').count()
        if total == 0:
            return mark_safe('<span style="color: #6c757d;">بدون قسط</span>')
        color = 'green' if paid == total else ('orange' if paid > 0 else 'red')
        return format_html(
            '<span style="color: {};">{}/{} پرداخت</span>',
            color, paid, total
        )
    installments_status.short_description = 'وضعیت اقساط'


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = [
        'policy_link', 'installment_number', 'amount_display',
        'due_date', 'status_colored', 'created_at'
    ]
    list_filter = ['status', 'due_date']
    search_fields = ['policy__policyholder', 'policy__plate_number']
    list_per_page = 50

    def policy_link(self, obj):
        url = f'/admin/policies/insurancepolicy/{obj.policy.pk}/change/'
        name = obj.policy.policyholder or '-'
        return mark_safe(f'<a href="{url}">{name[:30]}</a>')
    policy_link.short_description = 'بیمه گذار'
    policy_link.admin_order_field = 'policy__policyholder'

    def amount_display(self, obj):
        return f'{obj.amount:,}'
    amount_display.short_description = 'مبلغ (ریال)'

    def status_colored(self, obj):
        colors = {
            'paid': 'green',
            'pending': '#0d6efd',
            'overdue': 'red',
            'partial': 'orange',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'policy_link', 'amount_display', 'payment_date',
        'payment_method', 'reference_number', 'created_at'
    ]
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['policy__policyholder', 'reference_number']
    list_per_page = 50

    def policy_link(self, obj):
        url = f'/admin/policies/insurancepolicy/{obj.policy.pk}/change/'
        name = obj.policy.policyholder or '-'
        return mark_safe(f'<a href="{url}">{name[:30]}</a>')
    policy_link.short_description = 'بیمه گذار'

    def amount_display(self, obj):
        return f'{obj.amount:,}'
    amount_display.short_description = 'مبلغ (ریال)'


@admin.register(GuaranteeCheck)
class GuaranteeCheckAdmin(admin.ModelAdmin):
    list_display = ['policy_link', 'check_number', 'bank_name', 'amount_display', 'due_date', 'status_colored', 'created_at']
    list_filter = ['status', 'bank_name']
    search_fields = ['check_number', 'policy__policyholder']

    def policy_link(self, obj):
        url = f'/admin/policies/insurancepolicy/{obj.policy.pk}/change/'
        return mark_safe(f'<a href="{url}">{obj.policy.policyholder[:30]}</a>')
    policy_link.short_description = 'بیمه گذار'

    def amount_display(self, obj):
        return f'{obj.amount:,}'
    amount_display.short_description = 'مبلغ (ریال)'

    def status_colored(self, obj):
        colors = {'pending': '#0d6efd', 'cleared': '#2e7d32', 'returned': '#c62828'}
        return mark_safe(f'<span style="color: {colors.get(obj.status, "black")};">{obj.get_status_display()}</span>')
    status_colored.short_description = 'وضعیت'


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ['label', 'category', 'value']
    list_filter = ['category', 'value']


@admin.register(Endorsement)
class EndorsementAdmin(admin.ModelAdmin):
    list_display = ['policy_link', 'amount_display', 'reason_short', 'date', 'previous_total_display', 'new_total_display', 'created_at']
    list_filter = ['date']
    search_fields = ['policy__policyholder', 'reason']

    def policy_link(self, obj):
        return mark_safe(f'<a href="/admin/policies/insurancepolicy/{obj.policy.pk}/change/">{obj.policy.policyholder[:30]}</a>')
    policy_link.short_description = 'بیمه گذار'

    def amount_display(self, obj):
        return f'{obj.amount:,}'
    amount_display.short_description = 'مبلغ الحاقیه'

    def reason_short(self, obj):
        return obj.reason[:40] + '...' if len(obj.reason) > 40 else obj.reason
    reason_short.short_description = 'دلیل'

    def previous_total_display(self, obj):
        return f'{obj.previous_total:,}'
    previous_total_display.short_description = 'قبل'

    def new_total_display(self, obj):
        return f'{obj.new_total:,}'
    new_total_display.short_description = 'بعد'
