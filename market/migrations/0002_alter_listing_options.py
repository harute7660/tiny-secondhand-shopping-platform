from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="listing",
            options={
                "ordering": ("-created_at",),
                "permissions": [
                    ("block_listing", "Can block reported listings"),
                    ("purge_listing", "Can permanently purge listings"),
                ],
            },
        ),
    ]
