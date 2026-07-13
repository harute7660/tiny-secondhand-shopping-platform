import uuid

from django import forms
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse

from .models import MAX_TRANSFER_POINTS, Listing, Message, Report
from .services import can_users_interact, process_listing_image


class ProtectedListingImageInput(forms.ClearableFileInput):
    template_name = "market/widgets/protected_listing_image_input.html"
    clear_checkbox_label = "현재 이미지 삭제"
    initial_text = "현재 이미지"
    input_text = "새 이미지 선택"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        instance = getattr(value, "instance", None)
        listing_pk = getattr(instance, "pk", None)
        if context["widget"]["is_initial"] and listing_pk:
            context["widget"]["current_image_url"] = reverse(
                "market:listing_image",
                args=[listing_pk],
            )
        return context


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = (
            "title",
            "description",
            "price_points",
            "category",
            "condition",
            "region",
            "image",
        )
        labels = {
            "title": "제목",
            "description": "상품 설명",
            "price_points": "가격 (DEMO POINT)",
            "category": "카테고리",
            "condition": "상품 상태",
            "region": "거래 지역",
            "image": "상품 이미지",
        }
        help_texts = {
            "image": "JPEG, PNG, WebP · 5MB 이하 · 1,200만 픽셀 이하",
        }
        widgets = {
            "image": ProtectedListingImageInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                    "class": "image-upload-input",
                }
            ),
        }

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("제목을 입력해 주세요.")
        return title

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if not description:
            raise forms.ValidationError("상품 설명을 입력해 주세요.")
        return description

    def clean_region(self):
        region = self.cleaned_data["region"].strip()
        if not region:
            raise forms.ValidationError("거래 지역을 입력해 주세요.")
        return region

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if isinstance(image, UploadedFile):
            return process_listing_image(image)
        return image


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body",)
        labels = {"body": "메시지"}
        widgets = {"body": forms.Textarea(attrs={"maxlength": 1_000, "rows": 3})}

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("메시지를 입력해 주세요.")
        return body


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        # Reporter and target are derived from the authenticated route context.
        fields = ("category", "details")
        labels = {"category": "신고 유형", "details": "상세 내용"}
        widgets = {"details": forms.Textarea(attrs={"maxlength": 2_000, "rows": 5})}

    def clean_details(self):
        details = self.cleaned_data["details"].strip()
        if not details:
            raise forms.ValidationError("신고 사유를 입력해 주세요.")
        return details


class TransferForm(forms.Form):
    recipient_username = forms.CharField(max_length=150, label="받는 사용자")
    amount = forms.IntegerField(
        min_value=1,
        max_value=MAX_TRANSFER_POINTS,
        label="송금할 DEMO POINT",
    )
    idempotency_key = forms.UUIDField(
        initial=uuid.uuid4,
        widget=forms.HiddenInput,
    )

    def __init__(self, *args, actor=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor if actor is not None else user
        self.recipient = None

    def clean_recipient_username(self):
        return self.cleaned_data["recipient_username"].strip()

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("recipient_username")
        if not username:
            return cleaned_data

        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        try:
            recipient = user_model._default_manager.get(**{f"{username_field}__iexact": username})
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            self.add_error("recipient_username", "송금할 수 없는 사용자입니다.")
            return cleaned_data

        if not self.actor or not can_users_interact(self.actor, recipient):
            self.add_error("recipient_username", "송금할 수 없는 사용자입니다.")
            return cleaned_data

        self.recipient = recipient
        cleaned_data["recipient"] = recipient
        return cleaned_data
