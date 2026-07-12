from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_user_options"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="loginattempt",
            index=models.Index(
                fields=["window_started"],
                name="acct_login_window_idx",
            ),
        ),
    ]
