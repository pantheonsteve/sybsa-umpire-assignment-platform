from django.db import migrations

LEGACY_TIME_MAPPING = {
    '2:45': '14:45',
    '4:00': '16:00',
    '5:30': '17:30',
    '6:00': '18:00',
}

REVERSE_TIME_MAPPING = {new: old for old, new in LEGACY_TIME_MAPPING.items()}


def convert_legacy_times(apps, schema_editor):
    Game = apps.get_model('assignments', 'Game')
    UmpireAvailability = apps.get_model('assignments', 'UmpireAvailability')

    for old_time, new_time in LEGACY_TIME_MAPPING.items():
        Game.objects.filter(time=old_time).update(time=new_time)
        UmpireAvailability.objects.filter(time_slot=old_time).update(time_slot=new_time)


def revert_legacy_times(apps, schema_editor):
    Game = apps.get_model('assignments', 'Game')
    UmpireAvailability = apps.get_model('assignments', 'UmpireAvailability')

    for new_time, old_time in REVERSE_TIME_MAPPING.items():
        Game.objects.filter(time=new_time).update(time=old_time)
        UmpireAvailability.objects.filter(time_slot=new_time).update(time_slot=old_time)


class Migration(migrations.Migration):
    dependencies = [
        ('assignments', '0013_alter_game_time_alter_umpireavailability_time_slot'),
    ]

    operations = [
        migrations.RunPython(convert_legacy_times, reverse_code=revert_legacy_times),
    ]
