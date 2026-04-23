from django.db import migrations


def set_assigner_flag(apps, schema_editor):
    Umpire = apps.get_model('assignments', 'Umpire')
    Umpire.objects.filter(email='treasurer@sybsa.org').update(is_assigner=True)


def unset_assigner_flag(apps, schema_editor):
    Umpire = apps.get_model('assignments', 'Umpire')
    Umpire.objects.filter(email='treasurer@sybsa.org').update(is_assigner=False)


class Migration(migrations.Migration):
    dependencies = [
        ('assignments', '0005_umpire_is_assigner'),
    ]

    operations = [
        migrations.RunPython(set_assigner_flag, reverse_code=unset_assigner_flag),
    ]
