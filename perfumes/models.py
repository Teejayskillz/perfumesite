# perfumes/models.py
from django.db import models
from django.contrib.auth.models import User

class Perfume(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    url = models.URLField(blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    rating_value = models.FloatField(blank=True, null=True)
    rating_count = models.PositiveIntegerField(blank=True, null=True)
    year = models.CharField(max_length=10, blank=True, null=True)

    top_notes = models.TextField(blank=True, null=True)
    middle_notes = models.TextField(blank=True, null=True)
    base_notes = models.TextField(blank=True, null=True)

    perfumer1 = models.CharField(max_length=255, blank=True, null=True)
    perfumer2 = models.CharField(max_length=255, blank=True, null=True)

    mainaccord1 = models.CharField(max_length=255, blank=True, null=True)
    mainaccord2 = models.CharField(max_length=255, blank=True, null=True)
    mainaccord3 = models.CharField(max_length=255, blank=True, null=True)
    mainaccord4 = models.CharField(max_length=255, blank=True, null=True)
    mainaccord5 = models.CharField(max_length=255, blank=True, null=True)

    description = models.TextField(blank=True, null=True) 
    image = models.ImageField(upload_to="perfumes/", blank=True, null=True) 
    image_url = models.URLField(max_length=500, blank=True, null=True)
    

    def __str__(self):
        return f"{self.name} by {self.brand}"
    
class Review(models.Model):
    perfume = models.ForeignKey('Perfume', on_delete=models.CASCADE, related_name='reviews')
    name = models.CharField(max_length=100) 
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)  # 🔹 New field

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.name} on {self.perfume.name}"
   