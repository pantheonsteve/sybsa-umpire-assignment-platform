from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import subprocess
import os
import tempfile
from datetime import datetime


class Command(BaseCommand):
    help = 'Sync data from production database to local database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prod-url',
            type=str,
            help='Production database URL (if not in environment)',
        )
        parser.add_argument(
            '--no-backup',
            action='store_true',
            help='Skip creating a backup of local database',
        )

    def handle(self, *args, **options):
        # Get production database URL
        prod_url = options.get('prod_url') or os.environ.get('PRODUCTION_DATABASE_URL')
        
        if not prod_url:
            prod_url = "postgresql://umpireassigner_user:DRvGcZ0sqz9K7TQRwcJCHFNZXzhmcxEK@dpg-cslmrdt6l47c73abqa00-a.oregon-postgres.render.com/umpireassigner"
            self.stdout.write(self.style.WARNING(f'Using hardcoded production URL'))

        # Create timestamp for backups
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Step 1: Create local backup (unless skipped)
        if not options['no_backup']:
            self.stdout.write('Creating backup of local database...')
            local_backup = f'local_backup_{timestamp}.json'
            try:
                call_command('dumpdata', 
                           '--natural-primary', 
                           '--natural-foreign',
                           '--indent', '2',
                           '--output', local_backup)
                self.stdout.write(self.style.SUCCESS(f'✅ Local backup saved to {local_backup}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Could not create local backup: {e}'))
        
        # Step 2: Export production data using pg_dump
        self.stdout.write('\nExporting production database...')
        with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as tmp_file:
            dump_file = tmp_file.name
            
        try:
            # Run pg_dump
            result = subprocess.run(
                ['pg_dump', prod_url],
                capture_output=True,
                text=True,
                check=True
            )
            
            with open(dump_file, 'w') as f:
                f.write(result.stdout)
                
            self.stdout.write(self.style.SUCCESS('✅ Production data exported successfully'))
            
            # Step 3: Clear local database
            self.stdout.write('\nClearing local database...')
            # Get all models
            from django.apps import apps
            for model in apps.get_models():
                if model._meta.app_label == 'assignments':
                    model.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('✅ Local database cleared'))
            
            # Step 4: Import production data
            self.stdout.write('\nImporting production data to local database...')
            
            # Get local database settings
            db_settings = settings.DATABASES['default']
            
            # Build psql command based on database backend
            if 'postgresql' in db_settings['ENGINE']:
                psql_cmd = ['psql']
                if db_settings.get('HOST'):
                    psql_cmd.extend(['-h', db_settings['HOST']])
                if db_settings.get('PORT'):
                    psql_cmd.extend(['-p', str(db_settings['PORT'])])
                if db_settings.get('USER'):
                    psql_cmd.extend(['-U', db_settings['USER']])
                if db_settings.get('NAME'):
                    psql_cmd.extend(['-d', db_settings['NAME']])
                    
                # Import the dump
                with open(dump_file, 'r') as f:
                    subprocess.run(psql_cmd, stdin=f, check=True)
                    
                self.stdout.write(self.style.SUCCESS('✅ Production data imported successfully'))
            else:
                self.stdout.write(self.style.ERROR('❌ This command only works with PostgreSQL databases'))
                return
            
            # Step 5: Run migrations to ensure schema is up to date
            self.stdout.write('\nRunning migrations...')
            call_command('migrate', '--run-syncdb')
            self.stdout.write(self.style.SUCCESS('✅ Migrations completed'))
            
            # Clean up temp file
            os.unlink(dump_file)
            
            self.stdout.write(self.style.SUCCESS('\n🎉 Production data successfully synced to local!'))
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            self.stdout.write(self.style.ERROR('Make sure you have pg_dump and psql installed:'))
            self.stdout.write('  Mac: brew install postgresql')
            self.stdout.write('  Ubuntu: sudo apt-get install postgresql-client')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Unexpected error: {e}'))