from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0022_userwebsite'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='birthday_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='profile',
            constraint=models.CheckConstraint(
                check=models.Q(
                    ('birthday_date__isnull', True),
                    ('birthday_date__year', 1972),
                    _connector='OR',
                ),
                name='birthday_date_must_have_specific_year',
                violation_error_message=f"Birthdays must be saved as if they're in 1972",
            ),
        ),
    ]
