from django.db import models
import jsonfield

# Create your models here.


class GetCatchment(models.Model):
    time = models.DateTimeField()
    X = models.FloatField()
    Y = models.FloatField()
    uploadfolder = models.CharField(max_length=50)
    userfolder = models.CharField(max_length=50)
    filename = models.CharField(max_length=50)
    ip = models.CharField(max_length=50,default='null')
    catchment_result = jsonfield.JSONField()

