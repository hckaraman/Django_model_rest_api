from django.db import models


# Create your models here.
class BLogPost(models.Model):
    title = models.TextField()
    content = models.TextField(null=True, blank=True)

