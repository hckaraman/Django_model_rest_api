from django.http import HttpResponse
from django.shortcuts import render


def home_page(request):
    title = "At kafası"
    print(request.body)
    if request.user.is_authenticated:
        title = "Authenticated"
    return render(request, "home.html", {"title": title})
