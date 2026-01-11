# Generated migration to add schema_name field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0002_remove_client_schema_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='schema_name',
            field=models.CharField(db_index=True, default='public', max_length=63),
            preserve_default=False,
        ),
    ]
