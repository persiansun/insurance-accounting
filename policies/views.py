import json
import os
import jdatetime
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator

from .models import InsurancePolicy, Installment, Payment, InsuranceType, GuaranteeCheck, Endorsement
from .forms import (
    ExcelUploadForm, InstallmentGenerateForm,
    PaymentForm, InstallmentEditForm, PolicyEditForm, GuaranteeCheckForm, EndorsementForm
)
from .utils.excel_reader import parse_excel, preview_excel


class DashboardView(View):
    """Main dashboard showing summary and today's due installments"""

    def get(self, request):
        # Stats
        total_policies = InsurancePolicy.objects.count()
        total_installments = Installment.objects.count()
        paid_installments = Installment.objects.filter(status='paid').count()
        pending_installments = Installment.objects.filter(status='pending').count()
        overdue_installments = Installment.objects.filter(status='overdue').count()

        total_payments = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0

        # Stats by insurance type
        type_stats = []
        for it in InsuranceType.objects.filter(is_active=True):
            count = InsurancePolicy.objects.filter(insurance_type=it).count()
            if count > 0:
                type_stats.append({'name': it.name, 'slug': it.slug, 'count': count})

        # Today's due installments
        today = jdatetime.date.today().strftime('%Y/%m/%d')
        today_installments = Installment.objects.filter(
            due_date=today,
            status__in=['pending', 'overdue']
        ).select_related('policy')

        # Overdue installments
        overdue_list = Installment.objects.filter(
            status='overdue'
        ).select_related('policy').order_by('due_date')[:20]

        # Recent payments
        recent_payments = Payment.objects.select_related(
            'policy', 'installment'
        ).order_by('-created_at')[:10]

        context = {
            'total_policies': total_policies,
            'total_installments': total_installments,
            'paid_installments': paid_installments,
            'pending_installments': pending_installments,
            'overdue_installments': overdue_installments,
            'total_payments': total_payments,
            'today_installments': today_installments,
            'overdue_list': overdue_list,
            'recent_payments': recent_payments,
            'type_stats': type_stats,
            'today_date': today,
            'section': 'dashboard',
        }
        return render(request, 'policies/dashboard.html', context)


class UploadExcelView(View):
    """Upload and import Excel file"""

    def get(self, request):
        form = ExcelUploadForm()
        return render(request, 'policies/upload.html', {
            'form': form,
            'section': 'upload',
        })

    def post(self, request):
        # IMPORT: if user confirmed import from preview (no file upload)
        if request.POST.get('action') == 'import':
            file_path = request.POST.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                messages.error(request, 'فایل موقت یافت نشد. لطفاً دوباره آپلود کنید.')
                form = ExcelUploadForm()
                return render(request, 'policies/upload.html', {
                    'form': form,
                    'section': 'upload',
                })

            try:
                policies_data = parse_excel(file_path)
            except Exception as e:
                messages.error(request, f'خطا در خواندن فایل: {str(e)}')
                form = ExcelUploadForm()
                return render(request, 'policies/upload.html', {
                    'form': form,
                    'section': 'upload',
                })

            if not policies_data:
                messages.warning(request, 'هیچ داده‌ای در فایل یافت نشد')
                form = ExcelUploadForm()
                return render(request, 'policies/upload.html', {
                    'form': form,
                    'section': 'upload',
                })

            imported = 0
            updated = 0

            # Get or create insurance type from the parsed data
            type_slug = policies_data[0].get('_insurance_type_slug', '') if policies_data else ''
            insurance_type = None
            if type_slug:
                type_name = policies_data[0].get('_insurance_type_name', type_slug)
                insurance_type, _ = InsuranceType.objects.get_or_create(
                    slug=type_slug, defaults={'name': type_name}
                )

            for data in policies_data:
                policy_code = data.get('policy_code')
                if not policy_code:
                    continue

                existing = InsurancePolicy.objects.filter(policy_code=policy_code).first()
                if existing:
                    if data.get('policyholder'):
                        existing.policyholder = data.get('policyholder')
                    if insurance_type:
                        existing.insurance_type = insurance_type
                    existing.vehicle_value = data.get('vehicle_value')
                    # ... existing fields
                    if data.get('start_date'):
                        existing.start_date = data.get('start_date')
                    if data.get('end_date'):
                        existing.end_date = data.get('end_date')
                    if data.get('total_with_tax') is not None:
                        existing.total_with_tax = data.get('total_with_tax')
                    if data.get('total_premium') is not None:
                        existing.total_premium = data.get('total_premium')
                    if data.get('plate_number'):
                        existing.plate_number = data.get('plate_number')
                    if data.get('vehicle_type'):
                        existing.vehicle_type = data.get('vehicle_type')
                    if data.get('status'):
                        existing.status = data.get('status')
                    existing.raw_data = data.get('raw_data')
                    existing.save()
                    updated += 1
                else:
                    InsurancePolicy.objects.create(
                        policy_code=policy_code,
                        insurance_type=insurance_type,
                        policy_number=data.get('policy_number'),
                        policyholder=data.get('policyholder') or 'نامشخص',
                        contract_number=data.get('contract_number'),
                        contract_description=data.get('contract_description'),
                        status=data.get('status'),
                        start_date=data.get('start_date'),
                        end_date=data.get('end_date'),
                        issue_date=data.get('issue_date'),
                        duration_days=data.get('duration_days'),
                        total_premium=data.get('total_premium'),
                        vat=data.get('vat'),
                        total_with_tax=data.get('total_with_tax'),
                        plate_number=data.get('plate_number'),
                        vehicle_type=data.get('vehicle_type'),
                        vehicle_year=data.get('vehicle_year'),
                        body_coverage=data.get('body_coverage'),
                        financial_coverage=data.get('financial_coverage'),
                        vehicle_value=data.get('vehicle_value'),
                        agent_name=data.get('agent_name'),
                        archive_number=data.get('archive_number'),
                        raw_data=data.get('raw_data'),
                    )
                    imported += 1

            # Safely remove temp file (Windows + Persian filename workaround)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass  # Temp file cleanup is best-effort
            messages.success(
                request,
                f'✅ {imported} بیمه نامه جدید اضافه شد. '
                f'{updated} بیمه نامه به‌روزرسانی شد.'
            )
            return redirect('policies:policy_list')

        # UPLOAD: normal form upload with file
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']

            # Save to media temporarily
            from django.conf import settings
            media_dir = settings.MEDIA_ROOT
            os.makedirs(media_dir, exist_ok=True)

            file_path = os.path.join(media_dir, excel_file.name)
            with open(file_path, 'wb+') as f:
                for chunk in excel_file.chunks():
                    f.write(chunk)

            # Parse the file
            try:
                policies_data = parse_excel(file_path)
            except Exception as e:
                messages.error(request, f'خطا در خواندن فایل: {str(e)}')
                return render(request, 'policies/upload.html', {'form': form, 'section': 'upload'})

            if not policies_data:
                messages.warning(request, 'هیچ داده‌ای در فایل یافت نشد')
                return render(request, 'policies/upload.html', {'form': form, 'section': 'upload'})

            # Check for preview mode
            if request.POST.get('action') == 'preview':
                return render(request, 'policies/upload.html', {
                    'form': form,
                    'preview_data': policies_data,
                    'total_count': len(policies_data),
                    'file_path': file_path,
                    'insurance_type_name': policies_data[0].get('_insurance_type_name', '') if policies_data else '',
                    'insurance_type_slug': policies_data[0].get('_insurance_type_slug', '') if policies_data else '',
                    'section': 'upload',
                })

        return render(request, 'policies/upload.html', {
            'form': form,
            'section': 'upload',
        })


class PolicyListView(View):
    """List all insurance policies with search"""

    def get(self, request):
        search = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        type_filter = request.GET.get('type', '')

        policies = InsurancePolicy.objects.all()

        if search:
            policies = policies.filter(
                Q(policyholder__icontains=search) |
                Q(plate_number__icontains=search) |
                Q(policy_number__icontains=search) |
                Q(policy_code__icontains=search) |
                Q(vehicle_type__icontains=search)
            )

        if status_filter:
            policies = policies.filter(status=status_filter)

        if type_filter:
            policies = policies.filter(insurance_type__slug=type_filter)

        # Annotate with installment counts
        policies = policies.annotate(
            installments_count=Count('installments'),
            paid_count=Count('installments', filter=Q(installments__status='paid')),
        ).order_by('-created_at')

        # Pagination
        paginator = Paginator(policies, 25)
        page = request.GET.get('page', 1)
        policies_page = paginator.get_page(page)

        # Get unique statuses for filter
        all_statuses = (
            InsurancePolicy.objects.values_list('status', flat=True)
            .distinct().exclude(status__isnull=True).exclude(status='')
        )

        # Get insurance types for filter
        insurance_types = InsuranceType.objects.filter(is_active=True)

        context = {
            'policies': policies_page,
            'search': search,
            'status_filter': status_filter,
            'type_filter': type_filter,
            'all_statuses': all_statuses,
            'insurance_types': insurance_types,
            'section': 'policies',
        }
        return render(request, 'policies/policy_list.html', context)


class PolicyDetailView(View):
    """View policy details, installments, and payments"""

    def get(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        installments = policy.installments.all().order_by('installment_number')

        # Installment stats
        total_installment_amount = installments.aggregate(total=Sum('amount'))['total'] or 0
        paid_amount = policy.total_paid
        remaining = policy.total_debt

        payments = policy.payments.all().order_by('-created_at')[:20]

        # Forms
        installment_form = InstallmentGenerateForm(
            initial={
                'amount_per_installment': (
                    policy.amount_after_downpayment // 6 if policy.total_with_tax else 0
                ),
                'down_payment_amount': policy.down_payment or 0,
                'start_date': policy.start_date or jdatetime.date.today().strftime('%Y/%m/%d'),
            }
        )
        payment_form = PaymentForm(policy_id=policy.pk)
        guarantee_form = GuaranteeCheckForm()
        guarantee_checks = policy.guarantee_checks.all().order_by('-created_at')
        endorsement_form = EndorsementForm()
        endorsements = policy.endorsements.all().order_by('-created_at')

        context = {
            'policy': policy,
            'installments': installments,
            'total_installment_amount': total_installment_amount,
            'paid_amount': paid_amount,
            'remaining': remaining,
            'payments': payments,
            'installment_form': installment_form,
            'payment_form': payment_form,
            'guarantee_form': guarantee_form,
            'guarantee_checks': guarantee_checks,
            'endorsement_form': endorsement_form,
            'endorsements': endorsements,
            'section': 'policies',
        }
        return render(request, 'policies/policy_detail.html', context)


class PolicyDeleteView(View):
    """Delete a policy"""

    def post(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        policy.delete()
        messages.success(request, f'بیمه نامه {policy.policyholder} حذف شد')
        return redirect('policies:policy_list')


class PolicyEditView(View):
    """Edit policy information"""

    def get(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        form = PolicyEditForm(instance=policy)
        return render(request, 'policies/policy_edit.html', {
            'form': form,
            'policy': policy,
            'section': 'policies',
        })

    def post(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        form = PolicyEditForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'اطلاعات بیمه نامه {policy.policyholder} با موفقیت به‌روزرسانی شد'
            )
            return redirect('policies:policy_detail', pk=policy.pk)
        return render(request, 'policies/policy_edit.html', {
            'form': form,
            'policy': policy,
            'section': 'policies',
        })


class GenerateInstallmentsView(View):
    """Auto-generate installments for a policy"""

    def post(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        form = InstallmentGenerateForm(request.POST)

        if form.is_valid():
            count = form.cleaned_data['count']
            amount = form.cleaned_data['amount_per_installment']
            start_date = form.cleaned_data['start_date']
            interval_days = int(form.cleaned_data['interval'])  # '30' or '60'
            down_payment = form.cleaned_data.get('down_payment_amount') or 0

            # Save down_payment on policy if provided
            if down_payment > 0:
                policy.down_payment = down_payment
                policy.save(update_fields=['down_payment'])

            # Remove existing installments if user confirms
            if request.POST.get('replace') == 'yes':
                policy.installments.all().delete()

            # Generate installments
            created = 0
            current_date = start_date

            try:
                y, m, d = [int(x) for x in current_date.split('/')]
                current_jd = jdatetime.date(y, m, d)
            except Exception:
                messages.error(request, 'تاریخ شروع نامعتبر است')
                return redirect('policies:policy_detail', pk=pk)

            for i in range(count):
                due_date_str = current_jd.strftime('%Y/%m/%d')

                existing = Installment.objects.filter(
                    policy=policy, installment_number=i + 1
                ).first()

                if existing and request.POST.get('replace') != 'yes':
                    from datetime import timedelta
                    current_jd += timedelta(days=interval_days)
                    continue

                Installment.objects.update_or_create(
                    policy=policy,
                    installment_number=i + 1,
                    defaults={
                        'amount': amount,
                        'due_date': due_date_str,
                        'status': 'pending',
                    }
                )
                created += 1

                # Move to next date
                from datetime import timedelta
                current_jd += timedelta(days=interval_days)

            messages.success(
                request,
                f'{created} قسط برای {policy.policyholder} ایجاد شد'
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

        return redirect('policies:policy_detail', pk=pk)


class AddPaymentView(View):
    """Add a payment for a policy"""

    def post(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)

        # Check if this is a down payment
        is_down_payment = request.POST.get('payment_type') == 'down_payment'

        if is_down_payment:
            amount = request.POST.get('amount')
            payment_date = request.POST.get('payment_date')
            method = request.POST.get('payment_method', 'cash')
            ref = request.POST.get('reference_number', '')

            try:
                amount_int = int(amount) if amount else 0
            except (ValueError, TypeError):
                amount_int = 0

            if amount_int <= 0:
                messages.error(request, 'مبلغ نامعتبر است')
                return redirect('policies:policy_detail', pk=pk)

            # Mark down payment as paid
            policy.down_payment_paid = True
            policy.down_payment_date = payment_date
            policy.save(update_fields=['down_payment_paid', 'down_payment_date'])

            # Also create a payment record for the down payment
            Payment.objects.create(
                policy=policy,
                amount=amount_int,
                payment_date=payment_date,
                payment_method=method,
                reference_number=ref or None,
                notes='پیش پرداخت'
            )

            messages.success(
                request,
                f'✅ پیش پرداخت {amount_int:,} ریال ثبت شد'
            )
            return redirect('policies:policy_detail', pk=pk)

        # Check if this is a credit payment
        is_credit_payment = request.POST.get('payment_method') == 'credit'

        if is_credit_payment:
            amount = request.POST.get('amount')
            installment_id = request.POST.get('installment')
            try:
                amount_int = int(amount) if amount else 0
            except (ValueError, TypeError):
                amount_int = 0

            credit = policy.overpayment_credit or 0
            if amount_int <= 0 or amount_int > credit:
                messages.error(request, 'مبلغ نامعتبر یا بیش از اعتبار موجود')
                return redirect('policies:policy_detail', pk=pk)

            # Record payment using credit
            inst = Installment.objects.filter(pk=installment_id).first() if installment_id else None
            Payment.objects.create(
                policy=policy,
                installment=inst,
                amount=amount_int,
                payment_date=request.POST.get('payment_date', ''),
                payment_method='credit',
                notes='پرداخت از اعتبار'
            )

            # Deduct from credit
            policy.overpayment_credit = credit - amount_int
            policy.save(update_fields=['overpayment_credit'])

            messages.success(
                request,
                f'✅ مبلغ {amount_int:,} ریال از اعتبار کسر و به قسط اعمال شد'
            )
            return redirect('policies:policy_detail', pk=pk)

        # Normal installment payment flow
        form = PaymentForm(request.POST, policy_id=policy.pk)

        if form.is_valid():
            payment = form.save(commit=False)
            payment.policy = policy

            # If no installment selected, find the first unpaid one
            if not payment.installment:
                first_unpaid = policy.installments.filter(
                    status__in=['pending', 'overdue', 'partial']
                ).order_by('installment_number').first()
                payment.installment = first_unpaid

            try:
                payment.save()
                messages.success(
                    request,
                    f'واریزی {payment.amount:,} ریال برای {policy.policyholder} ثبت شد'
                )
            except Exception as e:
                messages.error(request, f'خطا در ثبت واریزی: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

        return redirect('policies:policy_detail', pk=pk)


class PolicyPaymentsView(View):
    """View all payments for a policy"""

    def get(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        payments = policy.payments.all().order_by('-created_at')

        paginator = Paginator(payments, 50)
        page = request.GET.get('page', 1)
        payments_page = paginator.get_page(page)

        context = {
            'policy': policy,
            'payments': payments_page,
            'section': 'policies',
        }
        return render(request, 'policies/policy_payments.html', context)


class AddGuaranteeCheckView(View):
    """Add a guarantee check for a policy"""

    def post(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        form = GuaranteeCheckForm(request.POST)
        if form.is_valid():
            check = form.save(commit=False)
            check.policy = policy
            check.save()
            messages.success(
                request,
                f'چک ضمانت به شماره {check.check_number} ثبت شد'
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
        return redirect('policies:policy_detail', pk=pk)


class DeleteGuaranteeCheckView(View):
    """Delete a guarantee check"""

    def post(self, request, pk):
        check = get_object_or_404(GuaranteeCheck, pk=pk)
        policy_pk = check.policy.pk
        check.delete()
        messages.success(request, 'چک ضمانت حذف شد')
        return redirect('policies:policy_detail', pk=policy_pk)


class AddEndorsementView(View):
    """Add an endorsement (الحاقیه) to a policy"""

    def post(self, request, pk):
        policy = get_object_or_404(InsurancePolicy, pk=pk)
        form = EndorsementForm(request.POST)
        if form.is_valid():
            endorsement = form.save(commit=False)
            endorsement.policy = policy
            try:
                endorsement.save()  # This auto-updates totals and installments
                messages.success(
                    request,
                    f'✅ الحاقیه به مبلغ {endorsement.amount:,} ریال ثبت شد. '
                    f'اقساط باقی‌مانده به‌روزرسانی شد.'
                )
            except Exception as e:
                messages.error(request, f'خطا در ثبت الحاقیه: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
        return redirect('policies:policy_detail', pk=pk)


class EditInstallmentView(View):
    """Edit a single installment"""

    def post(self, request, pk):
        installment = get_object_or_404(Installment, pk=pk)
        form = InstallmentEditForm(request.POST, instance=installment)

        if form.is_valid():
            form.save()
            messages.success(request, 'قسط با موفقیت ویرایش شد')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')

        return redirect('policies:policy_detail', pk=installment.policy.pk)


class DeleteInstallmentView(View):
    """Delete an installment"""

    def post(self, request, pk):
        installment = get_object_or_404(Installment, pk=pk)
        policy_pk = installment.policy.pk
        installment.delete()
        messages.success(request, 'قسط حذف شد')
        return redirect('policies:policy_detail', pk=policy_pk)


class ReportsView(View):
    """Main reports page"""

    def get(self, request):
        today = jdatetime.date.today()

        # Monthly stats (last 6 months)
        monthly_data = []
        for i in range(5, -1, -1):
            from datetime import timedelta
            month_date = today - timedelta(days=30 * i)
            month_str = month_date.strftime('%Y/%m')

            payments = Payment.objects.filter(
                payment_date__startswith=month_str
            )
            total = payments.aggregate(total=Sum('amount'))['total'] or 0
            count = payments.count()

            monthly_data.append({
                'month': month_date.strftime('%B %Y'),
                'total': total,
                'count': count,
            })

        # Status distribution
        status_counts = {
            'paid': Installment.objects.filter(status='paid').count(),
            'pending': Installment.objects.filter(status='pending').count(),
            'overdue': Installment.objects.filter(status='overdue').count(),
            'partial': Installment.objects.filter(status='partial').count(),
        }

        context = {
            'monthly_data': monthly_data,
            'status_counts': status_counts,
            'today': today.strftime('%Y/%m/%d'),
            'section': 'reports',
        }
        return render(request, 'policies/reports.html', context)


class DailyReportView(View):
    """Daily due installments report"""

    def get(self, request):
        date_str = request.GET.get(
            'date', jdatetime.date.today().strftime('%Y/%m/%d')
        )

        due_installments = Installment.objects.filter(
            due_date=date_str
        ).select_related('policy')

        overdue_installments = Installment.objects.filter(
            status='overdue'
        ).select_related('policy').order_by('due_date')

        context = {
            'date': date_str,
            'due_installments': due_installments,
            'overdue_installments': overdue_installments,
            'section': 'reports',
        }
        return render(request, 'policies/daily_report.html', context)


class ExportExcelView(View):
    """Export data to Excel"""

    def get(self, request):
        import pandas as pd
        from django.http import HttpResponse

        report_type = request.GET.get('type', 'policies')

        if report_type == 'policies':
            policies = InsurancePolicy.objects.all().values(
                'policyholder', 'policy_number', 'plate_number',
                'start_date', 'end_date', 'total_with_tax',
                'body_coverage', 'financial_coverage', 'status'
            )
            df = pd.DataFrame(list(policies))
            filename = 'policies.xlsx'

        elif report_type == 'installments':
            installments = Installment.objects.select_related('policy').all()
            data = []
            for inst in installments:
                data.append({
                    'بیمه گذار': inst.policy.policyholder,
                    'پلاک': inst.policy.plate_number,
                    'شماره قسط': inst.installment_number,
                    'مبلغ': inst.amount,
                    'تاریخ سررسید': inst.due_date,
                    'وضعیت': inst.get_status_display(),
                })
            df = pd.DataFrame(data)
            filename = 'installments.xlsx'

        elif report_type == 'payments':
            payments = Payment.objects.select_related('policy').all()
            data = []
            for p in payments:
                data.append({
                    'بیمه گذار': p.policy.policyholder,
                    'مبلغ': p.amount,
                    'تاریخ واریز': p.payment_date,
                    'روش پرداخت': p.get_payment_method_display(),
                    'شماره پیگیری': p.reference_number,
                })
            df = pd.DataFrame(data)
            filename = 'payments.xlsx'

        else:
            return redirect('policies:reports')

        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')

        return response


def ajax_policy_stats(request):
    """AJAX endpoint for dashboard stats"""
    total = InsurancePolicy.objects.count()
    with_installments = InsurancePolicy.objects.filter(
        installments__isnull=False
    ).distinct().count()

    return JsonResponse({
        'total_policies': total,
        'with_installments': with_installments,
    })
