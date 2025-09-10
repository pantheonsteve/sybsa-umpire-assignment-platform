from django.urls import path
from . import views

urlpatterns = [
    path('', views.weekly_schedule, name='weekly_schedule'),
    path('schedule/', views.weekly_schedule, name='weekly_schedule'),
    path('payments/', views.umpire_payments, name='umpire_payments'),
    path('unassigned/', views.unassigned_games, name='unassigned_games'),
    path('assign/<int:game_id>/', views.quick_assign_umpire, name='quick_assign_umpire'),
    path('games/<int:game_id>/edit/', views.edit_game, name='edit_game'),
    path('games/<int:game_id>/complete/', views.complete_game, name='complete_game'),
    path('games/bulk-create/', views.bulk_create_games, name='bulk_create_games'),
    path('import/', views.csv_import_home, name='csv_import_home'),
    path('import/<str:model_type>/', views.import_csv_data, name='import_csv'),
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    # Umpire portal
    path('umpire/dashboard/', views.umpire_dashboard, name='umpire_dashboard'),
    path('umpire/availability/', views.manage_availability, name='manage_availability'),
    # Admin views
    path('availability-grid/', views.availability_grid, name='availability_grid'),
    path('umpire/<int:umpire_id>/availability/edit/', views.edit_umpire_availability, name='edit_umpire_availability'),
    path('umpire-schedule/', views.umpire_schedule, name='umpire_schedule'),
]