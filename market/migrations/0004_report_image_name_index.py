from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0003_report_listing_snapshot"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="report",
            index=models.Index(
                fields=["listing_image_name_snapshot"],
                name="mkt_report_image_name_idx",
            ),
        ),
    ]
