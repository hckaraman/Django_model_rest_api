# Generated by Django 3.0.1 on 2019-12-24 19:55

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('catchment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='getcatchment',
            name='catchment_result',
            field=jsonfield.fields.JSONField(default=dict),
        ),
    ]
