from typing import ClassVar

from django import forms
from django.contrib import admin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db.models import Count
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter
from unfold.decorators import action

from apps.auths.models import User


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Passwords are stored as hashes.",
    )

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    
    actions = ("activate_users", "deactivate_users")

    list_display = (
        "email",
        "first_name",
        "last_name",
        "posts_count",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        ("is_active", ChoicesDropdownFilter),
        ("is_staff", ChoicesDropdownFilter),
        ("is_superuser", ChoicesDropdownFilter),
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("email",)

    fieldsets = (
        (
            "Personal information",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Important dates",
            {
                "fields": ("last_login",),
            },
        ),
    )

    add_fieldsets: ClassVar[tuple] = (
        (
            None,
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                )
            },
        ),
    )

    readonly_fields = ("last_login",)
    filter_horizontal = ("groups", "user_permissions")

    @admin.display(description="Posts", ordering="posts_count")
    def posts_count(self, obj: User) -> int:
        return obj.posts_count
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            posts_count=Count("posts")
        )

    @action(description="Activate selected users")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)

        self.message_user(
            request,
            f"{updated} users activated successfully.",
        )

    @action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        queryset = queryset.exclude(is_superuser=True)

        updated = queryset.update(is_active=False)

        self.message_user(
            request,
            f"{updated} users deactivated successfully.",
        )

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = self.add_form
            kwargs["fields"] = (
                "email",
                "first_name",
                "last_name",
                "password1",
                "password2",
            )
        return super().get_form(request, obj, **kwargs)
