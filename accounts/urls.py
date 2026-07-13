from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("me/", views.mypage_view, name="mypage"),
    path("me/password/", views.password_change_view, name="password_change"),
    path("users/<str:username>/", views.public_profile_view, name="public_profile"),
]
