from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('crud', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ] 