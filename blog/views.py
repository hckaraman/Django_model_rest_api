from django.shortcuts import render
from .models import BLogPost
from django.http import JsonResponse

# Create your views here.


def blog_post_detail_page(request, id):
    obj = BLogPost.objects.get(id=id)
    template_name = 'blog_post.detail.html'
    context = {"object": obj}
    return render(request, template_name, context)


def get_users(request):
    users = BLogPost.objects.all().values()
    users_list = list(users)
    return JsonResponse(users_list, safe=False)

