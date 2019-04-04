# Generated by Django 2.1.5 on 2019-04-04 09:02

from django.db import migrations, models
from payments.models import PAYMENT_TYPES
from job.tasks import verify_referee_discount

def actual_amount_initializer(apps, schema_editor):
    Transaction = apps.get_model('payments', 'StarsonaTransaction')
    transactions = Transaction.objects.all()
    for transaction in transactions:
        if transaction.amount:
            if transaction.payment_type is PAYMENT_TYPES.in_app:
                amount = round((float(transaction.amount) * (70.0/100.0)), 2)
            else:
                amount = float(transaction.amount)
            referee_discount = verify_referee_discount(transaction.celebrity.id)
            transaction.actual_amount = round((float(amount) * (referee_discount / 100.0)), 2)
        else:
            transaction.actual_amount = 0.0
        transaction.ambassador_amount = 0.0
        transaction.save()

class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0007_merge_20190321_0547'),
    ]

    operations = [
        migrations.AddField(
            model_name='starsonatransaction',
            name='actual_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Actual amount'),
        ),
        migrations.AddField(
            model_name='starsonatransaction',
            name='ambassador_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Ambassador amount'),
        ),
        migrations.RunPython(actual_amount_initializer)
    ]