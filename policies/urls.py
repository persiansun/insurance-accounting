from django.contrib import admin
from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('upload/', views.UploadExcelView.as_view(), name='upload'),
    path('policies/', views.PolicyListView.as_view(), name='policy_list'),
    path('policies/<int:pk>/', views.PolicyDetailView.as_view(), name='policy_detail'),
    path('policies/<int:pk>/edit/', views.PolicyEditView.as_view(), name='policy_edit'),
    path('policies/<int:pk>/delete/', views.PolicyDeleteView.as_view(), name='policy_delete'),
    path('policies/<int:pk>/generate-installments/', views.GenerateInstallmentsView.as_view(), name='generate_installments'),
    path('policies/<int:pk>/payments/', views.PolicyPaymentsView.as_view(), name='policy_payments'),
    path('policies/<int:pk>/payments/add/', views.AddPaymentView.as_view(), name='add_payment'),
    path('policies/<int:pk>/guarantee/add/', views.AddGuaranteeCheckView.as_view(), name='add_guarantee_check'),
    path('guarantee/<int:pk>/delete/', views.DeleteGuaranteeCheckView.as_view(), name='delete_guarantee_check'),
    path('policies/<int:pk>/endorsement/add/', views.AddEndorsementView.as_view(), name='add_endorsement'),
    path('endorsement/<int:pk>/edit/', views.EditEndorsementView.as_view(), name='edit_endorsement'),
    path('installments/<int:pk>/edit/', views.EditInstallmentView.as_view(), name='edit_installment'),
    path('installments/<int:pk>/delete/', views.DeleteInstallmentView.as_view(), name='delete_installment'),
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('reports/expiry/', views.ExpiryReportView.as_view(), name='expiry_report'),
    path('reports/expiry/export/excel/', views.ExportExpiryReportView.as_view(), name='export_expiry_report'),
    path('reports/daily/', views.DailyReportView.as_view(), name='daily_report'),
    path('reports/export/excel/', views.ExportExcelView.as_view(), name='export_excel'),
]
