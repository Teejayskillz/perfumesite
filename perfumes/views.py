from .models import Perfume
from django.http import JsonResponse
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Perfume, Review
from .forms import ReviewForm
from django.core.paginator import Paginator
import random



def home(request):
    perfumes = Perfume.objects.all().order_by('-id')  # Show newest first
    paginator = Paginator(perfumes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Random 5 featured perfumes for the slider
    featured_perfumes = random.sample(list(perfumes), min(5, len(perfumes)))

    # If infinite scroll request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'partials/perfume_list.html', {'perfumes': page_obj})

    return render(request, 'perfumes/home.html', {
        'perfumes': page_obj,
        'featured_perfumes': featured_perfumes,
    })


def perfume_list(request):
    perfumes = Perfume.objects.all().order_by('name')

    # Optional filters
    gender = request.GET.get('gender')
    country = request.GET.get('country')
    brand = request.GET.get('brand')
    accord = request.GET.get('accord')
    rating = request.GET.get('rating')

    if gender:
        perfumes = perfumes.filter(gender__iexact=gender)
    if country:
        perfumes = perfumes.filter(country__iexact=country)
    if brand:
        perfumes = perfumes.filter(brand__icontains=brand)
    if accord:
        perfumes = perfumes.filter(
            mainaccord1__icontains=accord
        ) | perfumes.filter(mainaccord2__icontains=accord)
    if rating:
        perfumes = perfumes.filter(rating_value__gte=rating)

    paginator = Paginator(perfumes, 12)  # show 12 perfumes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'perfumes/perfume_list.html', {'perfumes': page_obj})


def perfume_detail(request, pk):
    perfume = get_object_or_404(Perfume, pk=pk)
    reviews = perfume.reviews.filter(approved=True).order_by('-created_at')  # ✅ Only show approved reviews

    # ✅ Handle public review submission (no login required)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.perfume = perfume
            review.approved = False  # Needs admin approval
            review.save()
            messages.success(request, "Your review was submitted and is awaiting approval.")
            return redirect('perfume_detail', pk=pk)
    else:
        form = ReviewForm()

    # 🔹 Find similar perfumes
    main_accords = [
        perfume.mainaccord1,
        perfume.mainaccord2,
        perfume.mainaccord3,
        perfume.mainaccord4,
        perfume.mainaccord5,
    ]
    
    query = Q(brand__iexact=perfume.brand)
    for accord in main_accords:
        if accord:
            query |= (
                Q(mainaccord1__icontains=accord)
                | Q(mainaccord2__icontains=accord)
                | Q(mainaccord3__icontains=accord)
                | Q(mainaccord4__icontains=accord)
                | Q(mainaccord5__icontains=accord)
            )
    
    similar_perfumes = Perfume.objects.filter(query).exclude(pk=perfume.pk)[:4]

    context = {
        'perfume': perfume,
        'similar_perfumes': similar_perfumes,
        'reviews': reviews,
        'form': form,
        'absolute_url': request.build_absolute_uri(),
    }

    return render(request, 'perfumes/perfume_detail.html', context)



from django.http import JsonResponse

def compare_perfumes(request):
    perfume_ids = request.GET.getlist('perfumes')
    perfumes = Perfume.objects.filter(id__in=perfume_ids)
    all_perfumes = Perfume.objects.all().order_by('brand', 'name')

    context = {
        'perfumes': perfumes,
        'all_perfumes': all_perfumes,
    }

    # ✅ HTMX partial response for live updates
    if request.headers.get('HX-Request'):
        return render(request, 'perfumes/partials/compare_table.html', context)

    return render(request, 'perfumes/compare.html', context)


# 🔍 Live Suggestions for Autosuggest dropdowns
def perfume_suggestions(request):
    query = request.GET.get('q', '').strip()
    perfumes = Perfume.objects.filter(name__istartswith=query)[:10] if query else []
    return render(request, 'perfumes/partials/suggestions.html', {'perfumes': perfumes})


def filter_perfumes(request):
    gender = request.GET.get('gender')
    country = request.GET.get('country')
    brand_or_name = request.GET.get('brand')  # renamed for clarity
    accord = request.GET.get('accord')
    min_rating = request.GET.get('rating')

    perfumes = Perfume.objects.all()

    if gender:
        perfumes = perfumes.filter(gender__iexact=gender)

    if country:
        perfumes = perfumes.filter(country__icontains=country)

    # ✅ Search by brand OR perfume name
    if brand_or_name:
        perfumes = perfumes.filter(
            models.Q(brand__icontains=brand_or_name) |
            models.Q(name__icontains=brand_or_name)
        )

    if accord:
        perfumes = perfumes.filter(
            models.Q(mainaccord1__icontains=accord) |
            models.Q(mainaccord2__icontains=accord) |
            models.Q(mainaccord3__icontains=accord) |
            models.Q(mainaccord4__icontains=accord) |
            models.Q(mainaccord5__icontains=accord)
        )

    if min_rating:
        perfumes = perfumes.filter(rating_value__gte=float(min_rating))

    html = render_to_string("perfumes/partials/perfume_list.html", {"perfumes": perfumes})
    return HttpResponse(html)
