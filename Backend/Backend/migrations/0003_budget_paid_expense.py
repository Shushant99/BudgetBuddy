import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budgetbuddy', '0002_report_created_at_report_paid_expense'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='paid_expense',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='paid_report',
                to='budgetbuddy.expense',
            ),
        ),
        migrations.AddField(
            model_name='budget',
            name='paid_expense',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='paid_budget',
                to='budgetbuddy.expense',
            ),
        ),
    ]
