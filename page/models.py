from django.db import models
from ckeditor.fields import RichTextField

class Page(models.Model):
    """
    Model to store content for dynamic pages (e.g., About, Contact).
    Content can be managed via the Django Admin interface.
    """
    title = models.CharField(
        max_length=200, 
        unique=True,
        help_text="The title displayed on the page and used to generate the slug."
    )
    
    slug = models.SlugField(
        max_length=200, 
        unique=True,
        help_text="The URL path for the page (e.g., 'about' results in /about/). Must be unique."
    )
    
    content = RichTextField()
    
    # --- SEO & ATGS Fields (Crucial for boosting SEO) ---
    seo_description = models.CharField(
        max_length=160, 
        blank=True, 
        help_text="A brief, compelling description for search engine results (meta description)."
    )
    seo_keywords = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Comma-separated list of primary keywords (meta keywords)."
    )
    
    # Utility Fields
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # Human-readable representation of the object
        return self.title

    def get_absolute_url(self):
        # Returns the full URL path for the page
        from django.urls import reverse
        return reverse('page_detail', kwargs={'slug': self.slug})
    
    class Meta:
        verbose_name = "Dynamic Page"
        verbose_name_plural = "Dynamic Pages"
        ordering = ['title']
