from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import User

GENERIC_LOGIN_ERROR = _("로그인할 수 없습니다. 입력 정보를 확인하거나 잠시 후 다시 시도해 주세요.")


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # Never expose privilege, suspension, or staff fields to public input.
        fields = ("username",)
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "autocomplete": "username",
                    "autocapitalize": "none",
                    "spellcheck": "false",
                },
            ),
        }

    def clean_username(self):
        username = User.normalize_username_value(self.cleaned_data["username"])
        if User._default_manager.filter(username__iexact=username).exists():
            raise ValidationError(
                _("이미 사용 중인 사용자 이름입니다."),
                code="unique",
            )
        return username


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": GENERIC_LOGIN_ERROR,
        "inactive": GENERIC_LOGIN_ERROR,
    }

    username = forms.CharField(
        label=_("사용자 이름"),
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                "autofocus": True,
            },
        ),
    )
    password = forms.CharField(
        label=_("비밀번호"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean_username(self):
        return User.normalize_username_value(self.cleaned_data["username"])

    def confirm_login_allowed(self, user):
        try:
            super().confirm_login_allowed(user)
        except ValidationError as error:
            raise ValidationError(
                GENERIC_LOGIN_ERROR,
                code="invalid_login",
            ) from error

        if user.is_suspended:
            raise ValidationError(
                GENERIC_LOGIN_ERROR,
                code="invalid_login",
            )


class ProfileForm(forms.ModelForm):
    """Allow a member to update only the public biography field."""

    bio = forms.CharField(
        label="소개글",
        required=False,
        max_length=500,
        strip=True,
        widget=forms.Textarea(
            attrs={
                "autocomplete": "off",
                "maxlength": "500",
                "rows": 6,
            },
        ),
        help_text="공개 프로필에 표시됩니다. 최대 500자까지 입력할 수 있습니다.",
    )

    class Meta:
        model = User
        # Explicit allowlist prevents privilege and account-state assignment.
        fields = ("bio",)
