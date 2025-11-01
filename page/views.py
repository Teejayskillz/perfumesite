from django.views.generic import DetailView
from .models import Page

class PageDetailView(DetailView):
    """
    Displays a single Page object, fetched by its unique 'slug'.
    
    This view uses the slug provided in the URL to look up a Page instance
    in the database, and sends that instance as 'page' to the 
    'pages/page_detail.html' template.
    """
    model = Page
    template_name = 'page/page_detail.html' 
    slug_field = 'slug'                     
    context_object_name = 'page'            
    
    def get_queryset(self):
        # Crucial security and logic: only allow published pages to be accessed.
        return Page.objects.filter(is_published=True)

