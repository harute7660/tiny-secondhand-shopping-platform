from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.global_chat, name="global_chat"),
    path("messages/", views.global_chat_messages, name="global_chat_messages"),
    path("send/", views.global_chat_send, name="global_chat_send"),
]
