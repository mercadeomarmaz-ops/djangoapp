from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("music_publisher", "0011_alter_alternatetitle_title_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cwrexport",
            name="generated_filename",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True),
        ),
    ]
