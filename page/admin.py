from django.contrib import admin
from .models import Page

class PageAdmin(admin.ModelAdmin):
    """
    Custom administration settings for the Page model.
    """
    list_display = ('title', 'slug', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'content', 'seo_description')
    
    # Automatically generate the slug based on the title
    prepopulated_fields = {'slug': ('title',)} 

    # Group the fields logically in the admin form
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'content', 'is_published'),
        }),
        ('SEO Information (ATGS)', {
            'classes': ('collapse',), # Makes the SEO section collapsible
            'description': 'These fields are critical for search engine optimization and internal site links.',
            'fields': ('seo_description', 'seo_keywords'),
        }),
    )

admin.site.register(Page, PageAdmin)
