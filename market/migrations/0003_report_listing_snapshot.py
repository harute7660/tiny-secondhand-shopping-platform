from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("market", "0002_alter_listing_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="listing_category_snapshot",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_condition_snapshot",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_description_snapshot",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_image_name_snapshot",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_image_sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_price_snapshot",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_region_snapshot",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_status_snapshot",
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name="report",
            name="listing_title_snapshot",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddConstraint(
            model_name="report",
            constraint=models.UniqueConstraint(
                condition=models.Q(("listing__isnull", False), ("status", "OPEN")),
                fields=("reporter", "listing"),
                name="mkt_report_open_listing_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="report",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "OPEN"), ("target_user__isnull", False)),
                fields=("reporter", "target_user"),
                name="mkt_report_open_user_uniq",
            ),
        ),
    ]
