from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('profile/', views.profile_view, name='profile'),
    path('home/', views.home_view, name='home'),
    path('send-request/<int:user_id>/', views.send_request_view, name='send_request'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('respond-request/<int:req_id>/', views.respond_request_view, name='respond_request'),
    path('chat/<int:req_id>/', views.chat_view, name='chat'),
    path('chat-ajax/<int:req_id>/', views.chat_ajax_view, name='chat_ajax'),
    path('requests/sent/', views.requests_sent_view, name='requests_sent'),
    path('requests/received/', views.requests_received_view, name='requests_received'),
    path('chat-list/', views.chat_list_view, name='chat_list'),
    path('user-profile/<int:user_id>/', views.user_profile_view, name='user_profile'),
]