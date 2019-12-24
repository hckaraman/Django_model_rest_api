from django.shortcuts import render
from django.http import JsonResponse
from .Script import basin_delineation
from .Script import runall
from .models import GetCatchment
import datetime


def get_catchment(request, X, Y, uploadfolder, userfolder, filename):
    data = {"X": X, "Y": Y, "uploadfolder": uploadfolder, "userfolder": userfolder, "filename": filename}

    # requests = GetCatchment.objects.all().values()
    # print(requests)
    ip = visitor_ip_address(request)
    x = basin_delineation.catch(float(X), float(Y), uploadfolder,
                                userfolder,
                                filename)
    req = GetCatchment(time=datetime.datetime.now(), X=X, Y=Y, uploadfolder=uploadfolder, userfolder=userfolder,
                       filename=filename, ip=ip, catchment_result=x)
    req.save()
    return JsonResponse(x, safe=False)


def runAll(request, arg):
    resut = runall.run_all(arg)
    return JsonResponse(resut, safe=False)


def visitor_ip_address(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
