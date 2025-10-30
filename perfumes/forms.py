from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['name', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-gray-800 text-white border border-gray-700 rounded-lg p-2 mb-2',
                'placeholder': 'Your Name',
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full bg-gray-800 text-white border border-gray-700 rounded-lg p-2',
                'placeholder': 'Write your review...',
                'rows': 3,
            }),
        }
