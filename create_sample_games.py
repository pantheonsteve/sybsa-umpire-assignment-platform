#!/usr/bin/env python
"""
Script to create sample games for the specified dates and time slots.
Creates games for: 9-13-2025, 9-20-2025, 9-27-2025, 10-4-2025, 10-18-2025, 10-25-2025, and 11-1-2025
Time slots: 8:00 AM, 10:15 AM, 12:30 PM, and 2:45 PM
"""

import os
import django
from datetime import date

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umpire_assigner.settings')
django.setup()

from assignments.models import Game, Team, Town

def create_sample_games():
    # Game dates for 2025
    game_dates = [
        date(2025, 9, 13),
        date(2025, 9, 20),
        date(2025, 9, 27),
        date(2025, 10, 4),
        date(2025, 10, 18),
        date(2025, 10, 25),
        date(2025, 11, 1),
    ]
    
    # Time slots
    time_slots = ['8:00', '10:15', '12:30', '2:45']
    
    # Fields
    fields = ['A', 'B', 'C', 'D', 'E']
    
    # First, ensure we have some teams
    teams = list(Team.objects.all())
    if len(teams) < 2:
        print("Creating sample teams first...")
        # Create sample towns if needed
        town1, _ = Town.objects.get_or_create(name='Springfield')
        town2, _ = Town.objects.get_or_create(name='Shelbyville')
        town3, _ = Town.objects.get_or_create(name='Capital City')
        
        # Create sample teams
        team1, _ = Team.objects.get_or_create(
            town=town1, 
            level='Majors',
            defaults={'name': 'Red Sox', 'coach_id': None}
        )
        team2, _ = Team.objects.get_or_create(
            town=town1,
            level='AAA',
            defaults={'name': 'Yankees', 'coach_id': None}
        )
        team3, _ = Team.objects.get_or_create(
            town=town2,
            level='Majors',
            defaults={'name': 'Tigers', 'coach_id': None}
        )
        team4, _ = Team.objects.get_or_create(
            town=town2,
            level='AAA',
            defaults={'name': 'Cubs', 'coach_id': None}
        )
        team5, _ = Team.objects.get_or_create(
            town=town3,
            level='Majors',
            defaults={'name': 'Giants', 'coach_id': None}
        )
        team6, _ = Team.objects.get_or_create(
            town=town3,
            level='Minors',
            defaults={'name': 'Dodgers', 'coach_id': None}
        )
        
        teams = [team1, team2, team3, team4, team5, team6]
        print(f"Created {len(teams)} teams")
    
    # Create games
    games_created = 0
    games_skipped = 0
    
    for game_date in game_dates:
        for i, time_slot in enumerate(time_slots):
            # Use different fields for each time slot
            field = fields[i % len(fields)]
            
            # Rotate through teams
            home_team = teams[games_created % len(teams)]
            away_team = teams[(games_created + 1) % len(teams)]
            
            # Skip if teams are the same
            if home_team == away_team:
                away_team = teams[(games_created + 2) % len(teams)]
            
            # Check if game already exists
            existing = Game.objects.filter(
                date=game_date,
                time=time_slot,
                field=field
            ).exists()
            
            if not existing:
                Game.objects.create(
                    date=game_date,
                    time=time_slot,
                    field=field,
                    home_team=home_team,
                    away_team=away_team
                )
                games_created += 1
                print(f"Created game: {game_date} at {time_slot} on Field {field}")
            else:
                games_skipped += 1
    
    print(f"\nSummary:")
    print(f"Games created: {games_created}")
    print(f"Games skipped (already exist): {games_skipped}")
    print(f"Total games in system: {Game.objects.count()}")
    
    # Show game dates with slots
    print("\nGame schedule:")
    for game_date in game_dates:
        games = Game.objects.filter(date=game_date).order_by('time')
        if games:
            print(f"\n{game_date.strftime('%B %d, %Y')}:")
            for game in games:
                print(f"  - {game.get_time_display()} on Field {game.get_field_display()}: {game.home_team} vs {game.away_team}")

if __name__ == '__main__':
    create_sample_games()