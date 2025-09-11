from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum, Q, Count, Case, When, IntegerField
from django.db import transaction
from django.http import JsonResponse
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
from functools import wraps
import csv
import io
from .models import (
    Game, UmpireAssignment, Umpire, UmpirePayment,
    LeagueAdmin, Coach, Town, Team, PayRate, UmpireAvailability
)
from .utils import format_phone_number


def admin_required(view_func):
    """Decorator to check if user is admin (staff) and not just an umpire."""
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'You must be an administrator to access this page.')
            return redirect('weekly_schedule')
        return view_func(request, *args, **kwargs)
    return wrapped_view


def weekly_schedule(request):
    """Display the weekly schedule with games and umpire assignments."""
    # Get week parameter from request, default to current week
    week_offset = int(request.GET.get('week', 0))
    
    # Get sort parameters
    sort_by = request.GET.get('sort', 'time')  # default sort by time
    sort_order = request.GET.get('order', 'asc')
    
    # Get filter parameters
    filter_date = request.GET.get('filter_date', '')
    filter_time = request.GET.get('filter_time', '')
    filter_field = request.GET.get('filter_field', '')
    filter_home_team = request.GET.get('filter_home_team', '')
    filter_away_team = request.GET.get('filter_away_team', '')
    filter_umpire = request.GET.get('filter_umpire', '')
    
    # Calculate the start and end of the week
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    
    # Get games for the week
    # Add time_order annotation for proper chronological sorting
    games = Game.objects.filter(
        date__gte=start_of_week,
        date__lte=end_of_week
    ).annotate(
        time_order=Case(
            When(time='8:00', then=1),
            When(time='10:15', then=2),
            When(time='12:30', then=3),
            When(time='2:45', then=4),
            default=99,
            output_field=IntegerField()
        )
    ).select_related(
        'home_team', 'away_team', 'home_team__town', 'away_team__town',
        'home_team__coach', 'away_team__coach'
    ).prefetch_related(
        'assignments', 'assignments__umpire'
    )
    
    # Apply filters
    if filter_date:
        games = games.filter(date=filter_date)
    if filter_time:
        games = games.filter(time=filter_time)
    if filter_field:
        games = games.filter(field=filter_field)
    if filter_home_team:
        games = games.filter(home_team_id=filter_home_team)
    if filter_away_team:
        games = games.filter(away_team_id=filter_away_team)
    if filter_umpire:
        games = games.filter(assignments__umpire_id=filter_umpire).distinct()
    
    # Apply sorting
    if sort_by == 'time':
        # Sort primarily by time (chronologically), then by date and field
        if sort_order == 'desc':
            games = games.order_by('-time_order', 'date', 'field')
        else:
            games = games.order_by('time_order', 'date', 'field')
        order_field = None  # Skip the additional ordering below
    elif sort_by == 'field':
        order_field = 'field'
    elif sort_by == 'home':
        order_field = 'home_team__town__name'
    elif sort_by == 'away':
        order_field = 'away_team__town__name'
    elif sort_by == 'umpires':
        # Sort by number of umpires assigned (need annotation)
        from django.db.models import Count
        games = games.annotate(umpire_count=Count('assignments'))
        order_field = 'umpire_count'
    elif sort_by == 'datetime':
        # For datetime, we need to order by both date and time (chronologically)
        if sort_order == 'desc':
            games = games.order_by('-date', '-time_order', '-field')
        else:
            games = games.order_by('date', 'time_order', 'field')
        order_field = None  # Skip the additional ordering below
    else:
        # Default case - order by date then time chronologically
        games = games.order_by('date', 'time_order', 'field')
        order_field = None
    
    # Apply order direction if we have an order field
    if order_field:
        if sort_order == 'desc':
            games = games.order_by(f'-{order_field}', 'date', 'time')
        else:
            games = games.order_by(order_field, 'date', 'time')
    
    # Organize games by date (optional - can show all in one table)
    show_by_date = request.GET.get('view', 'by_date') == 'by_date'
    
    if show_by_date:
        games_by_date = {}
        for game in games:
            if game.date not in games_by_date:
                games_by_date[game.date] = []
            games_by_date[game.date].append(game)
        games_display = games_by_date
    else:
        games_display = list(games)
    
    # Get choices for filter dropdowns
    all_teams = Team.objects.select_related('town').order_by('town__name', 'level')
    all_umpires = Umpire.objects.order_by('last_name', 'first_name')
    
    context = {
        'games_by_date': games_display if show_by_date else None,
        'games_list': games_display if not show_by_date else None,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'week_offset': week_offset,
        'prev_week': week_offset - 1,
        'next_week': week_offset + 1,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'next_order': 'desc' if sort_order == 'asc' else 'asc',
        'show_by_date': show_by_date,
        # Filter values
        'filter_date': filter_date,
        'filter_time': filter_time,
        'filter_field': filter_field,
        'filter_home_team': filter_home_team,
        'filter_away_team': filter_away_team,
        'filter_umpire': filter_umpire,
        # Choices for dropdowns
        'all_teams': all_teams,
        'all_umpires': all_umpires,
        'time_choices': Game.TIME_CHOICES,
        'field_choices': Game.FIELD_CHOICES,
    }
    
    return render(request, 'assignments/weekly_schedule.html', context)


@admin_required
def umpire_payments(request):
    """Display umpire payment information."""
    from datetime import timedelta
    from django.db.models import Q
    
    # Get all umpires with their assignments and payments
    umpires = Umpire.objects.all().order_by('last_name', 'first_name')
    
    umpire_data = []
    for umpire in umpires:
        # Calculate projected payments (all assigned games, assuming they will work)
        projected_assignments = UmpireAssignment.objects.filter(
            umpire=umpire,
            worked_status='assigned'
        )
        
        # Calculate base pay for each assignment (even if not yet worked)
        projected_total = 0
        for assignment in projected_assignments:
            from .utils import get_pay_rate
            projected_total += get_pay_rate(assignment.umpire.patched, assignment.position)
        
        # Calculate actual owed from worked assignments only
        actual_owed = UmpireAssignment.objects.filter(
            umpire=umpire,
            worked_status='worked'
        ).aggregate(
            total=Sum('pay_amount')
        )['total'] or 0
        
        # Calculate total paid
        total_paid = UmpirePayment.objects.filter(
            umpire=umpire,
            paid=True
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate unpaid amounts
        actual_unpaid = actual_owed - total_paid
        projected_unpaid = projected_total + actual_owed - total_paid
        
        # Get all assignments grouped by date
        all_assignments = UmpireAssignment.objects.filter(
            umpire=umpire
        ).select_related('game', 'game__home_team', 'game__away_team').order_by('game__date', 'game__time')
        
        # Group assignments by date
        assignments_by_date = {}
        for assignment in all_assignments:
            date = assignment.game.date
            if date not in assignments_by_date:
                assignments_by_date[date] = {
                    'assignments': [],
                    'total_projected': Decimal('0.00'),
                    'total_earned': Decimal('0.00')
                }
            
            assignments_by_date[date]['assignments'].append(assignment)
            
            # Calculate payment based on worked status
            if assignment.worked_status == 'worked':
                assignments_by_date[date]['total_earned'] += assignment.pay_amount
            elif assignment.worked_status == 'assigned':
                from .utils import get_pay_rate
                projected_pay = get_pay_rate(assignment.umpire.patched, assignment.position)
                assignments_by_date[date]['total_projected'] += projected_pay
        
        # Get recent assignments (for backward compatibility)
        recent_assignments = UmpireAssignment.objects.filter(
            umpire=umpire
        ).select_related('game').order_by('-game__date')[:10]
        
        # Get payment history
        payment_history = UmpirePayment.objects.filter(
            umpire=umpire
        ).order_by('-period_end')
        
        umpire_data.append({
            'umpire': umpire,
            'projected_total': projected_total,
            'actual_owed': actual_owed,
            'total_paid': total_paid,
            'actual_unpaid': actual_unpaid,
            'projected_unpaid': projected_unpaid,
            'assignments_by_date': dict(sorted(assignments_by_date.items())),
            'recent_assignments': recent_assignments,
            'payment_history': payment_history,
        })
    
    # Calculate weekly payment totals
    # Get all games with assignments to determine week ranges
    games_with_assignments = Game.objects.filter(
        assignments__isnull=False
    ).distinct().order_by('date')
    
    weekly_totals = []
    if games_with_assignments.exists():
        # Start from the first game date
        current_date = games_with_assignments.first().date
        # Find the start of that week (Monday)
        week_start = current_date - timedelta(days=current_date.weekday())
        
        # Continue until the last game date
        last_date = games_with_assignments.last().date
        
        while week_start <= last_date:
            week_end = week_start + timedelta(days=6)
            
            # Calculate actual payments for this week (worked assignments only)
            week_worked_assignments = UmpireAssignment.objects.filter(
                game__date__gte=week_start,
                game__date__lte=week_end,
                worked_status='worked'
            )
            
            week_actual = week_worked_assignments.aggregate(
                total=Sum('pay_amount')
            )['total'] or 0
            
            # Calculate projected payments for this week (assigned but not yet worked)
            week_projected_assignments = UmpireAssignment.objects.filter(
                game__date__gte=week_start,
                game__date__lte=week_end,
                worked_status='assigned'
            )
            
            # Calculate projected amount
            week_projected = 0
            for assignment in week_projected_assignments:
                from .utils import get_pay_rate
                week_projected += get_pay_rate(assignment.umpire.patched, assignment.position)
            
            # Total expected for the week (actual + projected)
            week_total = week_actual + week_projected
            
            # Calculate amount paid for this week
            week_payments = UmpirePayment.objects.filter(
                period_start__lte=week_end,
                period_end__gte=week_start,
                paid=True
            )
            
            week_paid = week_payments.aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Count games and assignments for this week
            games_count = Game.objects.filter(
                date__gte=week_start,
                date__lte=week_end
            ).count()
            
            # Count all assignments (worked + assigned)
            all_week_assignments = UmpireAssignment.objects.filter(
                game__date__gte=week_start,
                game__date__lte=week_end
            )
            
            assignments_count = all_week_assignments.count()
            
            # Get umpire count for this week
            umpires_this_week = all_week_assignments.values('umpire').distinct().count()
            
            if games_count > 0:  # Only include weeks with games
                weekly_totals.append({
                    'week_start': week_start,
                    'week_end': week_end,
                    'total_projected': week_total,
                    'total_actual': week_actual,
                    'amount_due': week_total - week_paid,
                    'amount_paid': week_paid,
                    'games_count': games_count,
                    'assignments_count': assignments_count,
                    'umpires_count': umpires_this_week
                })
            
            # Move to next week
            week_start += timedelta(days=7)
    
    # Calculate grand totals
    grand_total_projected = sum(u['projected_total'] for u in umpire_data)
    grand_total_actual = sum(u['actual_owed'] for u in umpire_data)
    grand_total_paid = sum(u['total_paid'] for u in umpire_data)
    grand_total_unpaid_actual = sum(u['actual_unpaid'] for u in umpire_data)
    grand_total_unpaid_projected = sum(u['projected_unpaid'] for u in umpire_data)
    
    context = {
        'umpire_data': umpire_data,
        'weekly_totals': weekly_totals,
        'grand_total_projected': grand_total_projected,
        'grand_total_actual': grand_total_actual,
        'grand_total_paid': grand_total_paid,
        'grand_total_unpaid_actual': grand_total_unpaid_actual,
        'grand_total_unpaid_projected': grand_total_unpaid_projected,
    }
    
    return render(request, 'assignments/umpire_payments.html', context)


@admin_required
def csv_import_home(request):
    """Display the CSV import home page."""
    return render(request, 'assignments/csv_import_home.html')


@admin_required
def import_csv_data(request, model_type):
    """Handle CSV import for different model types."""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            messages.error(request, 'Please select a CSV file')
            return redirect('csv_import_home')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            return redirect('csv_import_home')
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            with transaction.atomic():
                if model_type == 'league_admins':
                    count = import_league_admins(reader)
                elif model_type == 'coaches':
                    count = import_coaches(reader)
                elif model_type == 'towns':
                    count = import_towns(reader)
                elif model_type == 'teams':
                    count = import_teams(reader)
                elif model_type == 'umpires':
                    count = import_umpires(reader)
                elif model_type == 'games':
                    count = import_games(reader)
                else:
                    messages.error(request, 'Invalid import type')
                    return redirect('csv_import_home')
                
                messages.success(request, f'Successfully imported {count} {model_type.replace("_", " ").title()}')
        except Exception as e:
            messages.error(request, f'Error importing CSV: {str(e)}')
        
        return redirect('csv_import_home')
    
    context = {
        'model_type': model_type,
        'model_name': model_type.replace('_', ' ').title(),
    }
    return render(request, 'assignments/csv_import_form.html', context)


def import_league_admins(reader):
    count = 0
    row_num = 1  # Start at 1 for header row
    for row in reader:
        row_num += 1
        try:
            LeagueAdmin.objects.update_or_create(
                email=row['email'],
                defaults={
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'phone': row['phone']
                }
            )
            count += 1
        except Exception as e:
            raise ValueError(f"Row {row_num}: Error importing league admin '{row.get('first_name', '')} {row.get('last_name', '')}' - {str(e)}")
    return count


def import_coaches(reader):
    count = 0
    row_num = 1  # Start at 1 for header row
    for row in reader:
        row_num += 1
        try:
            Coach.objects.update_or_create(
                email=row['email'],
                defaults={
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'phone': row['phone']
                }
            )
            count += 1
        except Exception as e:
            raise ValueError(f"Row {row_num}: Error importing coach '{row.get('first_name', '')} {row.get('last_name', '')}' - {str(e)}")
    return count


def import_towns(reader):
    count = 0
    row_num = 1  # Start at 1 for header row
    for row in reader:
        row_num += 1
        try:
            defaults = {'name': row['name']}
            if 'league_admin_email' in row and row['league_admin_email']:
                try:
                    league_admin = LeagueAdmin.objects.get(email=row['league_admin_email'])
                    defaults['league_admin'] = league_admin
                except LeagueAdmin.DoesNotExist:
                    raise ValueError(f"League admin with email '{row['league_admin_email']}' not found")
            
            Town.objects.update_or_create(
                name=row['name'],
                defaults=defaults
            )
            count += 1
        except Exception as e:
            raise ValueError(f"Row {row_num}: Error importing town '{row.get('name', '')}' - {str(e)}")
    return count


def import_teams(reader):
    count = 0
    row_num = 1  # Start at 1 for header row
    for row in reader:
        row_num += 1
        try:
            try:
                town = Town.objects.get(name=row['town'])
            except Town.DoesNotExist:
                raise ValueError(f"Town '{row['town']}' does not exist")
            
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
                    raise ValueError(f"Coach with email '{row['coach_email']}' not found")
            
            Team.objects.update_or_create(
                town=town,
                level=row['level'],
                name=row.get('name', ''),
                defaults=defaults
            )
            count += 1
        except Exception as e:
            team_desc = f"{row.get('town', '')} {row.get('level', '')}"
            if row.get('name'):
                team_desc += f" - {row['name']}"
            raise ValueError(f"Row {row_num}: Error importing team '{team_desc}' - {str(e)}")
    return count


def import_umpires(reader):
    count = 0
    row_num = 1  # Start at 1 for header row
    for row in reader:
        row_num += 1
        try:
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
        except Exception as e:
            raise ValueError(f"Row {row_num}: Error importing umpire '{row.get('first_name', '')} {row.get('last_name', '')}' - {str(e)}")
    return count


def import_games(reader):
    count = 0
    row_num = 1  # Start at 1 for header row
    for row in reader:
        row_num += 1
        game_desc = f"{row.get('date', '')} {row.get('time', '')} Field {row.get('field', '')}"
        
        try:
            # Try to find home team
            home_team_query = {
                'town__name': row.get('home_town', ''),
                'level': row.get('home_level', '')
            }
            if 'home_team_name' in row and row['home_team_name']:
                home_team_query['name'] = row['home_team_name']
            
            try:
                home_team = Team.objects.get(**home_team_query)
            except Team.DoesNotExist:
                if 'home_team_name' in row and row['home_team_name']:
                    # Team with specific name not found
                    raise ValueError(f"Home team '{row['home_town']} {row['home_level']} - {row['home_team_name']}' does not exist")
                else:
                    # Try to get without name to see if team exists at all
                    try:
                        Team.objects.get(
                            town__name=row['home_town'],
                            level=row['home_level']
                        )
                        # If we get here, team exists but query failed
                        raise ValueError(f"Home team matching criteria not found")
                    except Team.DoesNotExist:
                        raise ValueError(f"No {row['home_level']} team found for {row['home_town']}")
            except Team.MultipleObjectsReturned:
                teams = Team.objects.filter(
                    town__name=row['home_town'],
                    level=row['home_level']
                ).values_list('name', flat=True)
                team_names = ', '.join([name for name in teams if name])
                raise ValueError(f"Multiple {row['home_level']} teams found for {row['home_town']} ({team_names}). Please specify home_team_name column.")
            
            # Try to find away team
            away_team_query = {
                'town__name': row.get('away_town', ''),
                'level': row.get('away_level', '')
            }
            if 'away_team_name' in row and row['away_team_name']:
                away_team_query['name'] = row['away_team_name']
            
            try:
                away_team = Team.objects.get(**away_team_query)
            except Team.DoesNotExist:
                if 'away_team_name' in row and row['away_team_name']:
                    # Team with specific name not found
                    raise ValueError(f"Away team '{row['away_town']} {row['away_level']} - {row['away_team_name']}' does not exist")
                else:
                    # Try to get without name to see if team exists at all
                    try:
                        Team.objects.get(
                            town__name=row['away_town'],
                            level=row['away_level']
                        )
                        # If we get here, team exists but query failed
                        raise ValueError(f"Away team matching criteria not found")
                    except Team.DoesNotExist:
                        raise ValueError(f"No {row['away_level']} team found for {row['away_town']}")
            except Team.MultipleObjectsReturned:
                teams = Team.objects.filter(
                    town__name=row['away_town'],
                    level=row['away_level']
                ).values_list('name', flat=True)
                team_names = ', '.join([name for name in teams if name])
                raise ValueError(f"Multiple {row['away_level']} teams found for {row['away_town']} ({team_names}). Please specify away_team_name column.")
            
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
        except Exception as e:
            # Include row data in error for debugging
            row_data = f"[{', '.join([f'{k}={v}' for k, v in row.items() if v])}]"
            raise ValueError(f"Row {row_num}: {str(e)}\nRow data: {row_data}")
    return count


@admin_required
def unassigned_games(request):
    """Display games that need umpire assignments."""
    # Get filter parameters
    filter_date = request.GET.get('date')
    filter_field = request.GET.get('field')
    filter_level = request.GET.get('level')
    
    # Get sort parameters
    sort_by = request.GET.get('sort', 'datetime')
    sort_order = request.GET.get('order', 'asc')
    
    # Start with games that have fewer than 2 umpires assigned
    # Add time_order annotation for proper chronological sorting
    games = Game.objects.annotate(
        umpire_count=Count('assignments'),
        time_order=Case(
            When(time='8:00', then=1),
            When(time='10:15', then=2),
            When(time='12:30', then=3),
            When(time='2:45', then=4),
            default=99,
            output_field=IntegerField()
        )
    ).filter(
        Q(umpire_count=0) | Q(umpire_count=1)
    ).select_related(
        'home_team', 'away_team', 'home_team__town', 'away_team__town',
        'home_team__coach', 'away_team__coach'
    ).prefetch_related(
        'assignments', 'assignments__umpire'
    )
    
    # Apply filters
    if filter_date:
        games = games.filter(date=filter_date)
    if filter_field:
        games = games.filter(field=filter_field)
    if filter_level:
        games = games.filter(
            Q(home_team__level=filter_level) | Q(away_team__level=filter_level)
        )
    
    # Apply sorting
    if sort_by == 'time':
        order_field = 'time_order'  # Use chronological time ordering
    elif sort_by == 'field':
        order_field = 'field'
    elif sort_by == 'home':
        order_field = 'home_team__town__name'
    elif sort_by == 'away':
        order_field = 'away_team__town__name'
    elif sort_by == 'status':
        order_field = 'umpire_count'
    else:  # datetime (default) - chronological ordering
        order_field = None
        if sort_order == 'desc':
            games = games.order_by('-date', '-time_order', '-field')
        else:
            games = games.order_by('date', 'time_order', 'field')
    
    # Apply order direction if we have an order field
    if order_field:
        if sort_order == 'desc':
            games = games.order_by(f'-{order_field}', 'date', 'time_order')
        else:
            games = games.order_by(order_field, 'date', 'time_order')
    
    # Separate fully unassigned and partially assigned games
    fully_unassigned = []
    partially_assigned = []
    
    for game in games:
        assignment_count = game.assignments.count()
        
        # Get available umpires for this specific game
        all_umpires = Umpire.objects.all().order_by('last_name', 'first_name')
        available_umpires = []
        
        for umpire in all_umpires:
            # Check umpire availability for this game's date and time
            availability = UmpireAvailability.objects.filter(
                umpire=umpire,
                date=game.date,
                time_slot__in=[game.time, 'all']
            ).first()
            
            # Only include umpire if they've explicitly set availability as available or preferred
            if availability and availability.status in ['available', 'preferred']:
                # Check if umpire is already assigned to another game at this time
                # (Skip this check for Assigner umpires who can handle multiple games)
                if not umpire.is_assigner:
                    conflicting_assignment = UmpireAssignment.objects.filter(
                        umpire=umpire,
                        game__date=game.date,
                        game__time=game.time
                    ).exclude(game=game).exists()
                    
                    if conflicting_assignment:
                        continue
                
                available_umpires.append(umpire)
        
        game_data = {
            'game': game,
            'assignments': game.assignments.all(),
            'needed': 2 - assignment_count,
            'assignment_count': assignment_count,
            'available_umpires': available_umpires  # Game-specific available umpires
        }
        
        if assignment_count == 0:
            fully_unassigned.append(game_data)
        else:
            partially_assigned.append(game_data)
    
    # Note: removed the global available_umpires since each game now has its own list
    
    # Get statistics
    total_games = Game.objects.count()
    total_unassigned = len(fully_unassigned)
    total_partially = len(partially_assigned)
    total_fully_assigned = total_games - total_unassigned - total_partially
    
    context = {
        'fully_unassigned': fully_unassigned,
        'partially_assigned': partially_assigned,
        'filter_date': filter_date,
        'filter_field': filter_field,
        'filter_level': filter_level,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'next_order': 'desc' if sort_order == 'asc' else 'asc',
        'stats': {
            'total_games': total_games,
            'fully_assigned': total_fully_assigned,
            'partially_assigned': total_partially,
            'unassigned': total_unassigned,
            'coverage_percent': round((total_fully_assigned / total_games * 100) if total_games > 0 else 0, 1)
        }
    }
    
    return render(request, 'assignments/unassigned_games.html', context)


@admin_required
def quick_assign_umpire(request, game_id):
    """Quick assignment of umpire to a game."""
    if request.method == 'POST':
        game = get_object_or_404(Game, pk=game_id)
        umpire_id = request.POST.get('umpire_id')
        position = request.POST.get('position')
        
        if not umpire_id or not position:
            messages.error(request, 'Please select both an umpire and a position')
            return redirect('unassigned_games')
        
        umpire = get_object_or_404(Umpire, pk=umpire_id)
        
        # Check umpire availability
        availability = UmpireAvailability.objects.filter(
            umpire=umpire,
            date=game.date,
            time_slot__in=[game.time, 'all']
        ).first()
        
        # Umpire must have explicitly set availability as available or preferred
        if not availability or availability.status not in ['available', 'preferred']:
            messages.error(request, f'{umpire} is not available for this game date and time')
            return redirect('unassigned_games')
        
        # Check if umpire is already assigned to this game
        if UmpireAssignment.objects.filter(game=game, umpire=umpire).exists():
            messages.error(request, f'{umpire} is already assigned to this game')
            return redirect('unassigned_games')
        
        # Check if umpire is already assigned to another game at this time
        # (Skip this check for Assigner umpires who can handle multiple games)
        if not umpire.is_assigner:
            conflicting_assignment = UmpireAssignment.objects.filter(
                umpire=umpire,
                game__date=game.date,
                game__time=game.time
            ).exclude(game=game).first()
            
            if conflicting_assignment:
                messages.error(request, f'{umpire} is already assigned to another game at this time ({conflicting_assignment.game})')
                return redirect('unassigned_games')
        
        # Check how many umpires are already assigned
        current_assignments = game.assignments.count()
        if current_assignments >= 2:
            messages.error(request, 'This game already has 2 umpires assigned')
            return redirect('unassigned_games')
        
        # If this is the only umpire, they should be solo
        # If this is the second umpire, ensure proper plate/base assignment
        if current_assignments == 0 and position != 'solo':
            # First umpire can be solo, plate, or base
            pass
        elif current_assignments == 1:
            # Second umpire must complement the first
            existing_assignment = game.assignments.first()
            if existing_assignment.position == 'solo':
                messages.error(request, 'Cannot add a second umpire to a game with a solo umpire')
                return redirect('unassigned_games')
            elif existing_assignment.position == position:
                messages.error(request, f'This game already has a {position} umpire')
                return redirect('unassigned_games')
        
        # Create the assignment
        assignment = UmpireAssignment.objects.create(
            game=game,
            umpire=umpire,
            position=position
        )
        
        messages.success(request, f'Successfully assigned {umpire} as {position} umpire to {game}')
        return redirect('unassigned_games')
    
    return redirect('unassigned_games')


@admin_required
def bulk_create_games(request):
    """Bulk create multiple games at once using dropdowns."""
    if request.method == 'POST':
        # Get the form data
        dates = request.POST.getlist('date[]')
        times = request.POST.getlist('time[]')
        fields = request.POST.getlist('field[]')
        away_teams = request.POST.getlist('away_team[]')
        home_teams = request.POST.getlist('home_team[]')
        
        games_created = 0
        errors = []
        
        # Process each game
        for i in range(len(dates)):
            if dates[i] and times[i] and fields[i] and home_teams[i] and away_teams[i]:
                try:
                    # Check if teams are different
                    if home_teams[i] == away_teams[i]:
                        errors.append(f"Game {i+1}: Home and away teams cannot be the same")
                        continue
                    
                    # Check if game already exists
                    if Game.objects.filter(
                        date=dates[i],
                        time=times[i],
                        field=fields[i]
                    ).exists():
                        errors.append(f"Game {i+1}: A game already exists on {dates[i]} at {times[i]} on field {fields[i]}")
                        continue
                    
                    # Create the game
                    Game.objects.create(
                        date=dates[i],
                        time=times[i],
                        field=fields[i],
                        away_team_id=away_teams[i],
                        home_team_id=home_teams[i] 
                    )
                    games_created += 1
                except Exception as e:
                    errors.append(f"Game {i+1}: {str(e)}")
        
        if games_created > 0:
            messages.success(request, f'Successfully created {games_created} game(s)')
        
        for error in errors:
            messages.error(request, error)
        
        if games_created > 0:
            return redirect('bulk_create_games')
    
    # Get data for dropdowns
    teams = Team.objects.select_related('town').order_by('town__name', 'level', 'name')
    
    # Group teams by town and level for better display
    teams_list = []
    for team in teams:
        team_display = str(team)
        teams_list.append({
            'id': team.id,
            'display': team_display,
            'town': team.town.name,
            'level': team.level
        })
    
    # Get available times and fields from the model
    time_choices = Game.TIME_CHOICES
    field_choices = Game.FIELD_CHOICES
    
    # Suggest next available dates (next 30 days)
    from datetime import date, timedelta
    today = date.today()
    date_suggestions = []
    for i in range(30):
        suggested_date = today + timedelta(days=i)
        date_suggestions.append(suggested_date)
    
    context = {
        'teams': teams_list,
        'time_choices': time_choices,
        'field_choices': field_choices,
        'date_suggestions': date_suggestions,
    }
    
    return render(request, 'assignments/bulk_create_games.html', context)


@admin_required
def edit_game(request, game_id):
    """Edit a game and its umpire assignments."""
    game = get_object_or_404(Game, pk=game_id)
    
    # Get the week parameter to redirect back to the same week
    week_param = request.GET.get('week', request.POST.get('week', 0))
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete':
            # Delete the game
            game.delete()
            messages.success(request, 'Game deleted successfully')
            return redirect(f'/schedule/?week={week_param}')
        
        elif action == 'update':
            # Update game details
            try:
                game.date = request.POST.get('date')
                game.time = request.POST.get('time')
                game.field = request.POST.get('field')
                game.away_team_id = request.POST.get('away_team')
                game.home_team_id = request.POST.get('home_team')
                
                # Validate teams are different
                if game.home_team_id == game.away_team_id:
                    messages.error(request, 'Home and away teams cannot be the same')
                    return redirect(f'/games/{game_id}/edit/?week={week_param}')
                
                game.save()
                
                # Handle umpire assignments
                # First, get existing assignments
                existing_assignments = {a.id: a for a in game.assignments.all()}
                
                # Process umpire updates
                umpire_ids = request.POST.getlist('umpire_id[]')
                positions = request.POST.getlist('position[]')
                assignment_ids = request.POST.getlist('assignment_id[]')
                
                updated_assignment_ids = []
                
                for i in range(len(umpire_ids)):
                    if umpire_ids[i] and positions[i]:
                        if assignment_ids[i] and assignment_ids[i] != 'new':
                            # Update existing assignment
                            assignment_id = int(assignment_ids[i])
                            if assignment_id in existing_assignments:
                                assignment = existing_assignments[assignment_id]
                                assignment.umpire_id = umpire_ids[i]
                                assignment.position = positions[i]
                                assignment.save()
                                updated_assignment_ids.append(assignment_id)
                        else:
                            # Create new assignment
                            UmpireAssignment.objects.create(
                                game=game,
                                umpire_id=umpire_ids[i],
                                position=positions[i]
                            )
                
                # Delete assignments that were removed
                for assignment_id, assignment in existing_assignments.items():
                    if assignment_id not in updated_assignment_ids:
                        assignment.delete()
                
                messages.success(request, 'Game updated successfully')
                
                # Check where to redirect based on referrer
                next_url = request.POST.get('next', 'weekly_schedule')
                if 'unassigned' in next_url:
                    return redirect('unassigned_games')
                else:
                    return redirect(f'/schedule/?week={week_param}')
                    
            except Exception as e:
                messages.error(request, f'Error updating game: {str(e)}')
                return redirect(f'/games/{game_id}/edit/?week={week_param}')
    
    # Get data for form
    teams = Team.objects.select_related('town').order_by('town__name', 'level', 'name')
    
    # Get only available umpires for this game's date and time
    # First get all umpires
    all_umpires = Umpire.objects.all().order_by('last_name', 'first_name')
    
    # Filter to only those who are available and not already assigned at this time
    available_umpires = []
    for umpire in all_umpires:
        # Check if umpire has set availability for this date/time
        availability = UmpireAvailability.objects.filter(
            umpire=umpire,
            date=game.date,
            time_slot__in=[game.time, 'all']  # Check both specific time and "all day"
        ).first()
        
        # Only include umpire if they've explicitly set availability as available or preferred
        if availability and availability.status in ['available', 'preferred']:
            # Check if umpire is already assigned to another game at this time
            # (excluding the current game being edited)
            # Skip this check for Assigner umpires who can handle multiple games
            if not umpire.is_assigner:
                conflicting_assignment = UmpireAssignment.objects.filter(
                    umpire=umpire,
                    game__date=game.date,
                    game__time=game.time
                ).exclude(game=game).exists()
                
                if conflicting_assignment:
                    continue
            
            available_umpires.append(umpire)
    
    umpires = available_umpires
    time_choices = Game.TIME_CHOICES
    field_choices = Game.FIELD_CHOICES
    
    # Get current assignments
    assignments = list(game.assignments.select_related('umpire').all())
    
    # Prepare assignment data for template
    assignment_data = []
    for assignment in assignments:
        assignment_data.append({
            'id': assignment.id,
            'umpire_id': assignment.umpire.id,
            'position': assignment.position,
            'umpire_name': str(assignment.umpire)
        })
    
    context = {
        'game': game,
        'teams': teams,
        'umpires': umpires,
        'time_choices': time_choices,
        'field_choices': field_choices,
        'assignments': assignment_data,
        'referrer': request.META.get('HTTP_REFERER', '/'),
        'week_param': week_param
    }
    
    return render(request, 'assignments/edit_game.html', context)


def register(request):
    """Handle umpire self-registration."""
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        adult = request.POST.get('adult') == 'on'
        patched = request.POST.get('patched') == 'on'
        
        # Validation
        errors = []
        
        if not all([username, password, password2, email, first_name, last_name, phone]):
            errors.append('All fields are required except adult and patched status.')
        
        if password != password2:
            errors.append('Passwords do not match.')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        
        if User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        
        if Umpire.objects.filter(email=email).exists():
            errors.append('An umpire with this email already exists.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'assignments/register.html', {
                'form_data': request.POST
            })
        
        try:
            # Create user (inactive until admin approves)
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=False  # Requires admin approval
            )
            
            # Create umpire profile
            umpire = Umpire.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                adult=adult,
                patched=patched
            )
            
            messages.success(request, 'Registration successful! Your account is pending admin approval. You will be notified via email once approved.')
            
            # TODO: Send email notification to admin about new registration
            # TODO: Send confirmation email to umpire
            
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            # If user was created but umpire failed, delete the user
            if 'user' in locals():
                user.delete()
            return render(request, 'assignments/register.html', {
                'form_data': request.POST
            })
    
    return render(request, 'assignments/register.html')


def user_login(request):
    """Handle user login."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Redirect based on user type
            if hasattr(user, 'umpire_profile'):
                return redirect('umpire_dashboard')
            elif user.is_staff:
                return redirect('weekly_schedule')
            else:
                return redirect('weekly_schedule')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'assignments/login.html')


def user_logout(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login')


@login_required
def umpire_dashboard(request):
    """Dashboard for umpires to view their schedule and manage availability."""
    # Check if user is an umpire
    if not hasattr(request.user, 'umpire_profile'):
        messages.error(request, 'You must be an umpire to access this page')
        return redirect('weekly_schedule')
    
    umpire = request.user.umpire_profile
    
    # Get upcoming assignments
    today = date.today()
    upcoming_assignments = UmpireAssignment.objects.filter(
        umpire=umpire,
        game__date__gte=today
    ).select_related('game', 'game__home_team', 'game__away_team').order_by('game__date', 'game__time')
    
    # Get past assignments for the current month
    month_start = today.replace(day=1)
    past_assignments = UmpireAssignment.objects.filter(
        umpire=umpire,
        game__date__lt=today,
        game__date__gte=month_start
    ).select_related('game', 'game__home_team', 'game__away_team').order_by('-game__date', '-game__time')
    
    # Calculate earnings
    total_earned_this_month = past_assignments.aggregate(
        total=Sum('pay_amount')
    )['total'] or Decimal('0.00')
    
    total_upcoming = upcoming_assignments.aggregate(
        total=Sum('pay_amount')
    )['total'] or Decimal('0.00')
    
    # Get availability for the next 2 weeks
    two_weeks_from_now = today + timedelta(days=14)
    availability = UmpireAvailability.objects.filter(
        umpire=umpire,
        date__gte=today,
        date__lte=two_weeks_from_now
    ).order_by('date', 'time_slot')
    
    # Group availability by date for easier display
    availability_by_date = {}
    for avail in availability:
        if avail.date not in availability_by_date:
            availability_by_date[avail.date] = []
        availability_by_date[avail.date].append(avail)
    
    context = {
        'umpire': umpire,
        'upcoming_assignments': upcoming_assignments,
        'past_assignments': past_assignments,
        'total_earned_this_month': total_earned_this_month,
        'total_upcoming': total_upcoming,
        'availability': availability,
        'availability_by_date': availability_by_date,
        'today': today,
    }
    
    return render(request, 'assignments/umpire_dashboard.html', context)


@login_required
def manage_availability(request):
    """Allow umpires to manage their availability."""
    if not hasattr(request.user, 'umpire_profile'):
        messages.error(request, 'You must be an umpire to access this page')
        return redirect('weekly_schedule')
    
    umpire = request.user.umpire_profile
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        time_slot = request.POST.get('time_slot')
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if date_str and time_slot and status:
            # Parse the date
            from datetime import datetime as dt
            date_obj = dt.strptime(date_str, '%Y-%m-%d').date()
            
            availability, created = UmpireAvailability.objects.update_or_create(
                umpire=umpire,
                date=date_obj,
                time_slot=time_slot,
                defaults={
                    'status': status,
                    'notes': notes
                }
            )
            
            time_display = dict(UmpireAvailability.TIME_SLOT_CHOICES).get(time_slot, time_slot)
            if created:
                messages.success(request, f'Availability added for {date_str} at {time_display}')
            else:
                messages.success(request, f'Availability updated for {date_str} at {time_display}')
        
        return redirect('manage_availability')
    
    # Get game dates and slots
    game_dates_with_slots = UmpireAvailability.get_game_dates_with_slots()
    
    # Get existing availability
    today = date.today()
    availability = UmpireAvailability.objects.filter(
        umpire=umpire,
        date__gte=today
    ).order_by('date', 'time_slot')
    
    # Organize availability by date for easier display
    availability_by_date = {}
    for avail in availability:
        if avail.date not in availability_by_date:
            availability_by_date[avail.date] = []
        availability_by_date[avail.date].append(avail)
    
    context = {
        'umpire': umpire,
        'availability': availability,
        'availability_by_date': availability_by_date,
        'game_dates_with_slots': game_dates_with_slots,
        'availability_choices': UmpireAvailability.AVAILABILITY_CHOICES,
        'time_slot_choices': [c for c in UmpireAvailability.TIME_SLOT_CHOICES if c[0] != 'all'],
        'today': today,
    }
    
    return render(request, 'assignments/manage_availability.html', context)


@admin_required
def availability_grid(request):
    """Display a grid view of all umpires' availability."""
    # Get filter parameters
    filter_date = request.GET.get('date')
    
    # Get all umpires
    umpires = Umpire.objects.all().order_by('last_name', 'first_name')
    
    # Get game dates and slots
    dates_with_slots_dict = UmpireAvailability.get_game_dates_with_slots()
    
    # Convert to list of tuples with TIME_SLOT_CHOICES format
    game_dates_with_slots = []
    time_slot_display = dict(UmpireAvailability.TIME_SLOT_CHOICES)
    
    for date in sorted(dates_with_slots_dict.keys()):
        slots = []
        for time_slot in dates_with_slots_dict[date]:
            slots.append((time_slot, time_slot_display.get(time_slot, time_slot)))
        game_dates_with_slots.append((date, slots))
    
    # Filter dates if specified
    if filter_date:
        from datetime import datetime as dt
        filter_date_obj = dt.strptime(filter_date, '%Y-%m-%d').date()
        game_dates_with_slots = [
            (date, slots) for date, slots in game_dates_with_slots 
            if date == filter_date_obj
        ]
    
    # Build the grid data
    grid_data = []
    
    for umpire in umpires:
        # Get all availability for this umpire
        availabilities = UmpireAvailability.objects.filter(
            umpire=umpire
        )
        
        # Create a dict for quick lookup
        availability_dict = {}
        for avail in availabilities:
            key = f"{avail.date}_{avail.time_slot}"
            availability_dict[key] = avail.status
        
        # Build slots list in the same order as game_dates_with_slots
        slots = []
        for date, time_slots in game_dates_with_slots:
            first_of_date = True
            for slot in time_slots:
                key = f"{date}_{slot[0]}"
                slot_data = {
                    'status': availability_dict.get(key),
                    'first_of_date': first_of_date
                }
                slots.append(slot_data)
                first_of_date = False
        
        umpire_data = {
            'umpire': umpire,
            'slots': slots
        }
        
        grid_data.append(umpire_data)
    
    context = {
        'grid_data': grid_data,
        'game_dates_with_slots': game_dates_with_slots,
        'filter_date': filter_date,
    }
    
    return render(request, 'assignments/availability_grid.html', context)


@admin_required
def edit_umpire_availability(request, umpire_id):
    """Edit availability for a specific umpire."""
    umpire = get_object_or_404(Umpire, pk=umpire_id)
    
    # Get game dates and slots
    dates_with_slots_dict = UmpireAvailability.get_game_dates_with_slots()
    time_slot_display = dict(UmpireAvailability.TIME_SLOT_CHOICES)
    
    if request.method == 'POST':
        # Process availability updates
        updates_made = 0
        
        for date_str, time_slots in dates_with_slots_dict.items():
            for time_slot in time_slots:
                field_name = f"availability_{date_str}_{time_slot}"
                status = request.POST.get(field_name)
                
                if status in ['available', 'unavailable', 'preferred', 'none']:
                    if status == 'none':
                        # Delete the availability record
                        UmpireAvailability.objects.filter(
                            umpire=umpire,
                            date=date_str,
                            time_slot=time_slot
                        ).delete()
                    else:
                        # Create or update the availability record
                        availability, created = UmpireAvailability.objects.update_or_create(
                            umpire=umpire,
                            date=date_str,
                            time_slot=time_slot,
                            defaults={'status': status}
                        )
                        updates_made += 1
        
        messages.success(request, f'Updated availability for {umpire} ({updates_made} time slots changed)')
        return redirect('availability_grid')
    
    # Get current availability
    availabilities = UmpireAvailability.objects.filter(umpire=umpire)
    availability_dict = {}
    for avail in availabilities:
        key = f"{avail.date}_{avail.time_slot}"
        availability_dict[key] = avail.status
    
    # Build the form data
    game_dates_with_slots = []
    for date in sorted(dates_with_slots_dict.keys()):
        slots = []
        for time_slot in dates_with_slots_dict[date]:
            key = f"{date}_{time_slot}"
            slots.append({
                'time_slot': time_slot,
                'display': time_slot_display.get(time_slot, time_slot),
                'status': availability_dict.get(key, 'none'),
                'field_name': f"availability_{date}_{time_slot}"
            })
        game_dates_with_slots.append({
            'date': date,
            'slots': slots
        })
    
    context = {
        'umpire': umpire,
        'game_dates_with_slots': game_dates_with_slots,
    }
    
    return render(request, 'assignments/edit_umpire_availability.html', context)


@admin_required
def pending_registrations(request):
    """View and approve pending umpire registrations."""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        try:
            user = User.objects.get(id=user_id, is_active=False)
            
            if action == 'approve':
                user.is_active = True
                user.save()
                messages.success(request, f'Approved registration for {user.username}')
                # TODO: Send approval email to umpire
            elif action == 'reject':
                # Delete both user and umpire records
                if hasattr(user, 'umpire_profile'):
                    user.umpire_profile.delete()
                user.delete()
                messages.success(request, f'Rejected and deleted registration for {user.username}')
                # TODO: Send rejection email
        except User.DoesNotExist:
            messages.error(request, 'User not found')
        
        return redirect('pending_registrations')
    
    # Get all inactive users with umpire profiles (pending approval)
    pending_users = User.objects.filter(
        is_active=False,
        umpire_profile__isnull=False
    ).select_related('umpire_profile').order_by('-date_joined')
    
    context = {
        'pending_users': pending_users,
        'pending_count': pending_users.count(),
    }
    
    return render(request, 'assignments/pending_registrations.html', context)


@login_required
def umpire_schedule(request):
    """View umpire schedules with payment tracking."""
    # Get date filter from query params
    selected_date = request.GET.get('date')
    selected_umpire = request.GET.get('umpire')
    
    # Handle payment status update (staff only)
    if request.method == 'POST' and request.user.is_staff:
        assignment_id = request.POST.get('assignment_id')
        action = request.POST.get('action')
        
        try:
            assignment = UmpireAssignment.objects.get(id=assignment_id)
            
            if action == 'mark_paid':
                payment_method = request.POST.get('payment_method', '')
                payment_notes = request.POST.get('payment_notes', '')
                game_date = assignment.game.date
                
                # Check if payment record exists for this umpire and date
                payment, created = UmpirePayment.objects.get_or_create(
                    umpire=assignment.umpire,
                    period_start=game_date,
                    period_end=game_date,
                    defaults={
                        'amount': assignment.pay_amount,
                        'paid': True,
                        'paid_date': date.today(),
                        'payment_method': payment_method,
                        'notes': payment_notes
                    }
                )
                if not created:
                    payment.paid = True
                    payment.paid_date = date.today()
                    payment.payment_method = payment_method
                    payment.notes = payment_notes
                    payment.amount = assignment.pay_amount
                    payment.save()
                
                messages.success(request, f'Marked payment as paid for {assignment.umpire} via {payment_method}')
            
            elif action == 'mark_unpaid':
                # Find and update payment record
                try:
                    game_date = assignment.game.date
                    payment = UmpirePayment.objects.get(
                        umpire=assignment.umpire,
                        period_start=game_date,
                        period_end=game_date
                    )
                    payment.paid = False
                    payment.paid_date = None
                    payment.payment_method = ''
                    payment.notes = ''
                    payment.save()
                    messages.success(request, f'Marked payment as unpaid for {assignment.umpire}')
                except UmpirePayment.DoesNotExist:
                    pass
                    
        except UmpireAssignment.DoesNotExist:
            messages.error(request, 'Assignment not found')
        
        # Redirect to preserve filters
        redirect_url = request.path + '?'
        if selected_date:
            redirect_url += f'date={selected_date}&'
        if selected_umpire:
            redirect_url += f'umpire={selected_umpire}'
        return redirect(redirect_url.rstrip('&?') or request.path)
    
    # Build base query with time ordering
    assignments_query = UmpireAssignment.objects.select_related(
        'game', 'umpire', 'game__home_team', 'game__away_team'
    ).annotate(
        time_order=Case(
            When(game__time='8:00', then=1),
            When(game__time='10:15', then=2),
            When(game__time='12:30', then=3),
            When(game__time='2:45', then=4),
            default=99,
            output_field=IntegerField()
        )
    )
    
    # Apply filters
    if selected_date:
        try:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            assignments_query = assignments_query.filter(game__date=filter_date)
        except ValueError:
            messages.error(request, 'Invalid date format')
    
    if selected_umpire:
        assignments_query = assignments_query.filter(umpire_id=selected_umpire)
    
    # Order by date and time
    assignments_query = assignments_query.order_by('game__date', 'time_order', 'game__field')
    
    # Group assignments by umpire and date
    umpire_schedules = {}
    for assignment in assignments_query:
        umpire = assignment.umpire
        game_date = assignment.game.date
        
        if umpire not in umpire_schedules:
            umpire_schedules[umpire] = {}
        
        if game_date not in umpire_schedules[umpire]:
            umpire_schedules[umpire][game_date] = {
                'assignments': [],
                'total_pay': Decimal('0.00'),
                'payments': []
            }
        
        umpire_schedules[umpire][game_date]['assignments'].append(assignment)
        # Only add to total pay if umpire worked the game
        if assignment.worked_status == 'worked':
            umpire_schedules[umpire][game_date]['total_pay'] += assignment.pay_amount
    
    # Check payment status for each umpire and date
    for umpire in umpire_schedules:
        for game_date in umpire_schedules[umpire]:
            # Get payment for this specific umpire and date
            payments = UmpirePayment.objects.filter(
                umpire=umpire,
                period_start__lte=game_date,
                period_end__gte=game_date
            )
            umpire_schedules[umpire][game_date]['payments'] = list(payments)
    
    # Get all umpires for filter dropdown
    all_umpires = Umpire.objects.all().order_by('last_name', 'first_name')
    
    # Get unique dates for filter dropdown
    all_dates = Game.objects.values_list('date', flat=True).distinct().order_by('date')
    
    context = {
        'umpire_schedules': umpire_schedules,
        'selected_date': selected_date,
        'selected_umpire': selected_umpire,
        'all_umpires': all_umpires,
        'all_dates': all_dates,
    }
    
    return render(request, 'assignments/umpire_schedule.html', context)


@admin_required
def complete_game(request, game_id):
    """Mark game as complete and track umpire attendance."""
    game = get_object_or_404(Game, id=game_id)
    
    if request.method == 'POST':
        # Update game status
        game_status = request.POST.get('game_status')
        if game_status in ['completed', 'postponed', 'cancelled']:
            game.status = game_status
            game.save()
            
            # Update each umpire assignment
            for assignment in game.assignments.all():
                assignment_id = str(assignment.id)
                worked_status = request.POST.get(f'worked_status_{assignment_id}')
                
                if worked_status in ['worked', 'no_show', 'cancelled']:
                    assignment.worked_status = worked_status
                    
                    # Recalculate pay based on worked status
                    if worked_status == 'worked':
                        assignment.pay_amount = assignment.calculate_pay()
                    else:
                        assignment.pay_amount = Decimal('0.00')
                    
                    assignment.save()
            
            messages.success(request, f'Game {game} has been marked as {game.get_status_display()}')
            
            # Redirect back to schedule or specified return URL
            next_url = request.POST.get('next', 'weekly_schedule')
            return redirect(next_url)
    
    context = {
        'game': game,
        'assignments': game.assignments.all().select_related('umpire'),
        'status_choices': Game.STATUS_CHOICES,
        'worked_status_choices': UmpireAssignment.WORKED_STATUS_CHOICES,
    }
    
    return render(request, 'assignments/complete_game.html', context)


@admin_required
def update_assignment_pay(request, assignment_id):
    """AJAX endpoint to update assignment pay amount inline."""
    if request.method == 'POST':
        try:
            assignment = UmpireAssignment.objects.get(id=assignment_id)
            new_pay = request.POST.get('pay_amount')
            
            if new_pay:
                try:
                    # Convert to Decimal and validate
                    pay_amount = Decimal(new_pay)
                    if pay_amount < 0:
                        return JsonResponse({'success': False, 'error': 'Pay amount cannot be negative'})
                    
                    assignment.pay_amount = pay_amount
                    assignment.save()
                    
                    return JsonResponse({
                        'success': True, 
                        'new_amount': str(pay_amount),
                        'formatted_amount': f'${pay_amount:.2f}'
                    })
                except (ValueError, InvalidOperation):
                    return JsonResponse({'success': False, 'error': 'Invalid pay amount'})
            else:
                return JsonResponse({'success': False, 'error': 'Pay amount is required'})
                
        except UmpireAssignment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Assignment not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
