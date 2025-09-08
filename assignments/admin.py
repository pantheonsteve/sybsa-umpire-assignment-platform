from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
import csv
import io
from .models import (
    LeagueAdmin, Coach, Town, Team, Umpire, Game, 
    UmpireAssignment, UmpirePayment, PayRate
)


class CSVImportMixin:
    """Mixin to add CSV import functionality to admin classes"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_import_csv'),
        ]
        return custom_urls + urls
    
    def import_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, 'Please select a CSV file')
                return redirect('..')
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'File is not CSV type')
                return redirect('..')
            
            try:
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                
                with transaction.atomic():
                    count = self.process_csv_data(reader)
                    messages.success(request, f'Successfully imported {count} records')
            except Exception as e:
                messages.error(request, f'Error importing CSV: {str(e)}')
            
            return redirect('..')
        
        context = {
            'title': f'Import {self.model._meta.verbose_name_plural}',
            'opts': self.model._meta,
            'site_title': self.admin_site.site_title,
            'site_header': self.admin_site.site_header,
            'has_permission': True,
        }
        return render(request, 'admin/csv_import.html', context)
    
    def process_csv_data(self, reader):
        """Override this method in child classes to process CSV data"""
        raise NotImplementedError


@admin.register(LeagueAdmin)
class LeagueAdminAdmin(admin.ModelAdmin, CSVImportMixin):
    list_display = ('first_name', 'last_name', 'email', 'phone')
    search_fields = ('first_name', 'last_name', 'email')
    
    def process_csv_data(self, reader):
        count = 0
        for row in reader:
            LeagueAdmin.objects.update_or_create(
                email=row['email'],
                defaults={
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'phone': row['phone']
                }
            )
            count += 1
        return count


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin, CSVImportMixin):
    list_display = ('first_name', 'last_name', 'email', 'phone')
    search_fields = ('first_name', 'last_name', 'email')
    
    def process_csv_data(self, reader):
        count = 0
        for row in reader:
            Coach.objects.update_or_create(
                email=row['email'],
                defaults={
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'phone': row['phone']
                }
            )
            count += 1
        return count


@admin.register(Town)
class TownAdmin(admin.ModelAdmin, CSVImportMixin):
    list_display = ('name', 'league_admin')
    search_fields = ('name',)
    list_filter = ('league_admin',)
    
    def process_csv_data(self, reader):
        count = 0
        for row in reader:
            defaults = {'name': row['name']}
            if 'league_admin_email' in row and row['league_admin_email']:
                try:
                    league_admin = LeagueAdmin.objects.get(email=row['league_admin_email'])
                    defaults['league_admin'] = league_admin
                except LeagueAdmin.DoesNotExist:
                    pass
            
            Town.objects.update_or_create(
                name=row['name'],
                defaults=defaults
            )
            count += 1
        return count


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin, CSVImportMixin):
    list_display = ('town', 'level', 'name', 'coach')
    list_filter = ('level', 'town')
    search_fields = ('name', 'town__name', 'coach__first_name', 'coach__last_name')
    
    def process_csv_data(self, reader):
        count = 0
        for row in reader:
            town = Town.objects.get(name=row['town'])
            defaults = {
                'town': town,
                'level': row['level'],
            }
            
            if 'name' in row:
                defaults['name'] = row['name']
            
            if 'coach_email' in row and row['coach_email']:
                try:
                    coach = Coach.objects.get(email=row['coach_email'])
                    defaults['coach'] = coach
                except Coach.DoesNotExist:
                    pass
            
            Team.objects.update_or_create(
                town=town,
                level=row['level'],
                name=row.get('name', ''),
                defaults=defaults
            )
            count += 1
        return count


@admin.register(Umpire)
class UmpireAdmin(admin.ModelAdmin, CSVImportMixin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'adult', 'patched')
    list_filter = ('adult', 'patched')
    search_fields = ('first_name', 'last_name', 'email')
    
    def process_csv_data(self, reader):
        count = 0
        for row in reader:
            adult = row.get('adult', '').lower() in ['yes', 'true', '1']
            patched = row.get('patched', '').lower() in ['yes', 'true', '1']
            
            Umpire.objects.update_or_create(
                email=row['email'],
                defaults={
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'phone': row['phone'],
                    'adult': adult,
                    'patched': patched
                }
            )
            count += 1
        return count


class UmpireAssignmentInline(admin.TabularInline):
    model = UmpireAssignment
    extra = 2
    max_num = 2


@admin.register(Game)
class GameAdmin(admin.ModelAdmin, CSVImportMixin):
    list_display = ('date', 'time', 'field', 'home_team', 'away_team')
    list_filter = ('date', 'time', 'field')
    date_hierarchy = 'date'
    search_fields = ('home_team__town__name', 'away_team__town__name')
    inlines = [UmpireAssignmentInline]
    
    def process_csv_data(self, reader):
        count = 0
        for row in reader:
            # Try to find team by town, level, and name (if provided)
            home_team_query = {
                'town__name': row['home_town'],
                'level': row['home_level']
            }
            if 'home_team_name' in row and row['home_team_name']:
                home_team_query['name'] = row['home_team_name']
            
            away_team_query = {
                'town__name': row['away_town'],
                'level': row['away_level']
            }
            if 'away_team_name' in row and row['away_team_name']:
                away_team_query['name'] = row['away_team_name']
            
            try:
                home_team = Team.objects.get(**home_team_query)
            except Team.DoesNotExist:
                # If not found with name, try without name
                home_team = Team.objects.get(
                    town__name=row['home_town'],
                    level=row['home_level']
                )
            except Team.MultipleObjectsReturned:
                # If multiple teams found, user needs to specify team name
                raise ValueError(f"Multiple {row['home_level']} teams found for {row['home_town']}. Please specify home_team_name.")
            
            try:
                away_team = Team.objects.get(**away_team_query)
            except Team.DoesNotExist:
                # If not found with name, try without name
                away_team = Team.objects.get(
                    town__name=row['away_town'],
                    level=row['away_level']
                )
            except Team.MultipleObjectsReturned:
                # If multiple teams found, user needs to specify team name
                raise ValueError(f"Multiple {row['away_level']} teams found for {row['away_town']}. Please specify away_team_name.")
            
            Game.objects.update_or_create(
                date=row['date'],
                time=row['time'],
                field=row['field'],
                defaults={
                    'home_team': home_team,
                    'away_team': away_team
                }
            )
            count += 1
        return count


@admin.register(UmpireAssignment)
class UmpireAssignmentAdmin(admin.ModelAdmin):
    list_display = ('game', 'umpire', 'position', 'pay_amount')
    list_filter = ('position', 'game__date')
    search_fields = ('umpire__first_name', 'umpire__last_name', 'game__home_team__town__name')


@admin.register(UmpirePayment)
class UmpirePaymentAdmin(admin.ModelAdmin):
    list_display = ('umpire', 'amount', 'paid', 'period_start', 'period_end', 'paid_date')
    list_filter = ('paid', 'period_start', 'period_end')
    search_fields = ('umpire__first_name', 'umpire__last_name')
    date_hierarchy = 'period_end'
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        from datetime import date
        updated = queryset.update(paid=True, paid_date=date.today())
        messages.success(request, f'{updated} payments marked as paid')
    mark_as_paid.short_description = "Mark selected payments as paid"


@admin.register(PayRate)
class PayRateAdmin(admin.ModelAdmin):
    list_display = ('effective_date', 'solo_patched', 'solo_unpatched', 
                    'plate_patched', 'plate_unpatched', 'base_unpatched')
    list_filter = ('effective_date',)
    ordering = ('-effective_date',)
