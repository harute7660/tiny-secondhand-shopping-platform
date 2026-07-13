import re
import unicodedata
import uuid

from django import forms
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse

from .models import (
    MAX_REVIEW_BODY_LENGTH,
    MAX_TOTAL_LISTING_IMAGES,
    MAX_TRANSFER_POINTS,
    Listing,
    ListingDefect,
    Message,
    Report,
    Review,
    SavedSearch,
    normalize_saved_search_text,
)
from .services import MAX_IMAGE_BATCH_BYTES, can_users_interact, process_listing_image


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


class MultipleListingImageInput(forms.FileInput):
    allow_multiple_selected = True


class MultipleListingImageField(forms.Field):
    widget = MultipleListingImageInput

    def clean(self, value):
        files = list(value or [])
        if len(files) > MAX_TOTAL_LISTING_IMAGES:
            raise forms.ValidationError(
                f"상품 사진은 대표 사진을 포함해 최대 {MAX_TOTAL_LISTING_IMAGES}장입니다."
            )
        total_size = sum(max(getattr(item, "size", 0) or 0, 0) for item in files)
        if total_size > MAX_IMAGE_BATCH_BYTES:
            raise forms.ValidationError("한 요청의 이미지 파일 합계는 20MB 이하여야 합니다.")

        processed = []
        for item in files:
            try:
                processed.append(process_listing_image(item))
            except forms.ValidationError as exc:
                raise forms.ValidationError(
                    f"추가 사진을 확인해 주세요: {exc.messages[0]}"
                ) from exc
        return processed


class ListingForm(forms.ModelForm):
    extra_images = MultipleListingImageField(
        required=False,
        label="추가 상품 사진",
        help_text="대표 사진을 포함해 최대 5장 · 요청 합계 20MB 이하",
        widget=MultipleListingImageInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "class": "image-upload-input",
            }
        ),
    )
    remove_extra_images = forms.MultipleChoiceField(
        required=False,
        label="기존 추가 사진 삭제",
        choices=(),
        widget=forms.CheckboxSelectMultiple,
    )
    defects = forms.MultipleChoiceField(
        required=False,
        label="확인된 하자 항목",
        choices=ListingDefect.Code.choices,
        widget=forms.CheckboxSelectMultiple,
    )

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
            "extra_images",
            "remove_extra_images",
            "defect_disclosure",
            "defects",
            "defect_details",
        )
        labels = {
            "title": "제목",
            "description": "상품 설명",
            "price_points": "가격 (DEMO POINT)",
            "category": "카테고리",
            "condition": "상품 상태",
            "region": "거래 지역",
            "image": "대표 상품 이미지",
            "defect_disclosure": "하자 확인 상태",
            "defect_details": "하자 상세 설명",
        }
        help_texts = {
            "image": "JPEG, PNG, WebP · 5MB 이하 · 1,200만 픽셀 이하",
            "defect_details": "개인정보 없이 위치·크기·작동 영향을 1,000자 이하로 적어 주세요.",
        }
        widgets = {
            "image": ProtectedListingImageInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                    "class": "image-upload-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_defect_disclosure = (
            self.instance.defect_disclosure
            if self.instance and self.instance.pk
            else Listing.DefectDisclosure.UNKNOWN
        )
        self.fields["defect_disclosure"].required = False
        extra_images = []
        if self.instance and self.instance.pk:
            extra_images = list(self.instance.extra_images.order_by("position"))
            self.fields["defects"].initial = list(
                self.instance.defects.values_list("code", flat=True)
            )
        self.existing_extra_images = extra_images
        self.fields["remove_extra_images"].choices = [
            (str(item.pk), f"추가 사진 {index}") for index, item in enumerate(extra_images, start=2)
        ]
        if not extra_images:
            self.fields["remove_extra_images"].widget = forms.HiddenInput()

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

    def clean(self):
        cleaned = super().clean()
        image = cleaned.get("image")
        additions = cleaned.get("extra_images") or []
        removals = set(cleaned.get("remove_extra_images") or [])
        existing_extra_count = sum(
            1 for item in self.existing_extra_images if str(item.pk) not in removals
        )
        total_images = (1 if image else 0) + existing_extra_count + len(additions)
        if total_images > MAX_TOTAL_LISTING_IMAGES:
            self.add_error(
                "extra_images",
                "삭제 후 남는 사진까지 합쳐 최대 "
                f"{MAX_TOTAL_LISTING_IMAGES}장만 저장할 수 있습니다.",
            )

        disclosure = cleaned.get("defect_disclosure") or self.initial_defect_disclosure
        cleaned["defect_disclosure"] = disclosure
        defects = cleaned.get("defects") or []
        details = (cleaned.get("defect_details") or "").strip()
        cleaned["defect_details"] = details
        if disclosure == Listing.DefectDisclosure.PRESENT and not defects:
            self.add_error("defects", "하자 있음으로 선택했다면 항목을 하나 이상 골라 주세요.")
        if disclosure != Listing.DefectDisclosure.PRESENT and defects:
            self.add_error("defects", "하자 항목은 하자 있음 상태에서만 선택할 수 있습니다.")
        if ListingDefect.Code.OTHER in defects and not details:
            self.add_error("defect_details", "기타 하자의 상세 내용을 입력해 주세요.")
        return cleaned


class SavedSearchForm(forms.ModelForm):
    class Meta:
        model = SavedSearch
        fields = ("query", "category", "region")
        labels = {
            "query": "관심 검색어",
            "category": "카테고리",
            "region": "거래 지역",
        }

    @staticmethod
    def _clean_text(value, *, minimum=0):
        value = normalize_saved_search_text(value)
        if any(unicodedata.category(char).startswith("C") for char in value):
            raise forms.ValidationError("제어 문자가 포함된 검색 조건은 저장할 수 없습니다.")
        if value and len(value) < minimum:
            raise forms.ValidationError(f"{minimum}자 이상 입력해 주세요.")
        return value

    def clean_query(self):
        return self._clean_text(self.cleaned_data["query"], minimum=2)

    def clean_region(self):
        return self._clean_text(self.cleaned_data["region"])

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(name) for name in ("query", "category", "region")):
            raise forms.ValidationError("검색어, 카테고리, 지역 중 하나 이상을 지정해 주세요.")
        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")
        labels = {"rating": "평점", "body": "거래 후기"}
        widgets = {
            "rating": forms.RadioSelect(
                choices=((5, "5점"), (4, "4점"), (3, "3점"), (2, "2점"), (1, "1점"))
            ),
            "body": forms.Textarea(attrs={"rows": 5, "maxlength": MAX_REVIEW_BODY_LENGTH}),
        }
        help_texts = {
            "body": "개인정보·연락처 없이 실제 거래 경험을 "
            f"{MAX_REVIEW_BODY_LENGTH}자 이하로 적어 주세요.",
        }

    def clean_body(self):
        body = unicodedata.normalize("NFKC", self.cleaned_data["body"]).strip()
        if not body:
            raise forms.ValidationError("후기 내용을 입력해 주세요.")
        if any(unicodedata.category(char).startswith("C") and char not in "\n\t" for char in body):
            raise forms.ValidationError("후기에 제어 문자를 포함할 수 없습니다.")
        private_patterns = (
            r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
            r"(?:https?://|www\.)\S+",
            r"(?:\d[\s().-]?){7,}",
        )
        if any(re.search(pattern, body, flags=re.IGNORECASE) for pattern in private_patterns):
            raise forms.ValidationError(
                "전화번호·이메일·URL 등 개인정보는 공개 후기에 입력할 수 없습니다."
            )
        return body


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
