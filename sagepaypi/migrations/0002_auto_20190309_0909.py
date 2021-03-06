# Generated by Django 2.1.7 on 2019-03-09 09:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sagepaypi', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='reference_transaction',
            field=models.ForeignKey(blank=True, help_text='The referring transaction used for a "Repeat" or "Refund" transaction.', null=True, on_delete=django.db.models.deletion.CASCADE, to='sagepaypi.Transaction', verbose_name='Reference transaction'),
        ),
    ]
