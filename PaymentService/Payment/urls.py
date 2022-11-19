from django.urls import path
from django.contrib import admin
from .views import PaymentViewSet,PaymentHealthViewSet

urlpatterns=[
    path('Payment/<str:paymentUid>',PaymentViewSet.as_view({
        'get':'getPayment',
        'patch':'cancelPayment'
    })),
    path('Payment',PaymentViewSet.as_view({
        'get':'listePayment',
        'post':'createPayment'
    })),
    path('health',PaymentHealthViewSet.as_view({
        'get':'getHealth'
    })),
]