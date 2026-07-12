from django.urls import path

from . import views

app_name = "market"

urlpatterns = [
    path("", views.home, name="home"),
    path("safety/", views.safety, name="safety"),
    path("listings/new/", views.listing_create, name="listing_create"),
    path("listings/<uuid:pk>/", views.listing_detail, name="listing_detail"),
    path("listings/<uuid:pk>/edit/", views.listing_update, name="listing_update"),
    path("listings/<uuid:pk>/delete/", views.listing_delete, name="listing_delete"),
    path("listings/<uuid:pk>/status/", views.listing_status_update, name="listing_status_update"),
    path("listings/<uuid:pk>/image/", views.listing_image, name="listing_image"),
    path("listings/<uuid:pk>/favorite/", views.favorite_toggle, name="favorite_toggle"),
    path("listings/<uuid:pk>/contact/", views.conversation_start, name="conversation_start"),
    path("conversations/", views.conversation_list, name="conversation_list"),
    path("conversations/<uuid:pk>/", views.conversation_detail, name="conversation_detail"),
    path("users/<int:user_id>/block/", views.user_block_toggle, name="user_block_toggle"),
    path("reports/new/", views.report_create, name="report_create"),
    path("wallet/", views.wallet, name="wallet"),
    path("wallet/transfer/", views.transfer, name="transfer"),
]
