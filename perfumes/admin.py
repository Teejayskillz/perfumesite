from django.contrib import admin
from django.utils.html import format_html
from .models import Perfume
from .models import Review


@admin.register(Perfume)
class PerfumeAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "name",
        "brand",
        "country",
        "gender",
        "rating_value",
        "year",
    )
    list_filter = ("brand", "country", "gender", "year")
    search_fields = ("name", "brand", "country", "top_notes", "middle_notes", "base_notes")
    ordering = ("brand", "name")
    list_per_page = 25

    fieldsets = (
        ("General Info", {
            "fields": ("name", "brand", "url", "country", "gender", "year")
        }),
        ("Ratings", {
            "fields": ("rating_value", "rating_count")
        }),
        ("Notes", {
            "fields": ("top_notes", "middle_notes", "base_notes")
        }),
        ("Perfumers", {
            "fields": ("perfumer1", "perfumer2")
        }),
        ("Main Accords", {
            "fields": ("mainaccord1", "mainaccord2", "mainaccord3", "mainaccord4", "mainaccord5")
        }),
        ("Description & Image", {
            "fields": ("description", "image_preview", "image_url", "image"),
        }),
    )

    readonly_fields = ("image_preview",)

    def thumbnail(self, obj):
        """Show a small thumbnail in list view."""
        if obj.image:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:6px;object-fit:cover;" />',
                obj.image.url,
            )
        elif obj.image_url:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:6px;object-fit:cover;" />',
                obj.image_url,
            )
        return "—"
    thumbnail.short_description = "Image"

    def image_preview(self, obj):
        """Show larger preview in detail view."""
        if obj.image:
            return format_html(
                '<img src="{}" width="180" style="border-radius:10px;box-shadow:0 0 6px #aaa;" />',
                obj.image.url,
            )
        elif obj.image_url:
            return format_html(
                '<img src="{}" width="180" style="border-radius:10px;box-shadow:0 0 6px #aaa;" />',
                obj.image_url,
            )
        return "No image available"
    image_preview.short_description = "Preview"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('perfume', 'name', 'approved', 'created_at')
    list_filter = ('approved',)
    search_fields = ('name', 'content')
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)
