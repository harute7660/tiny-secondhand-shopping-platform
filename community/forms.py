from django import forms

from .models import GlobalChatMessage


class GlobalChatMessageForm(forms.ModelForm):
    class Meta:
        model = GlobalChatMessage
        # The authenticated request, never a client field, decides the sender.
        fields = ("body",)
        labels = {"body": "전체 채팅 메시지"}
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "maxlength": 1_000,
                    "rows": 3,
                    "autocomplete": "off",
                    "placeholder": "모든 사용자에게 보낼 메시지를 입력하세요.",
                }
            )
        }

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("메시지를 입력해 주세요.")
        return body
