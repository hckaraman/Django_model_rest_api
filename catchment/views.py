from django.shortcuts import render
from django.http import JsonResponse
from .Script import basin_delineation
from .Script import runall


def get_catchment(request, X, Y, uploadfolder, userfolder, filename):
    data = {"X": X, "Y": Y, "uploadfolder": uploadfolder, "userfolder": userfolder, "filename": filename}

    x = basin_delineation.catch(float(X), float(Y), uploadfolder,
                                userfolder,
                                filename)

    return JsonResponse(x, safe=False)

def runAll(request, arg):
    resut = runall.run_all(arg)
    return JsonResponse(resut, safe=False)


