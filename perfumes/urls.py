from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('list/', views.perfume_list, name='perfume_list'),
    path('<int:pk>/', views.perfume_detail, name='perfume_detail'),
    path('compare/', views.compare_perfumes, name='compare_perfumes'),
    path('compare/suggestions/', views.perfume_suggestions, name='perfume_suggestions'),
    path('perfume-suggestions/', views.perfume_suggestions, name='perfume_suggestions'),
    path('filter/', views.filter_perfumes, name='filter_perfumes'),
]