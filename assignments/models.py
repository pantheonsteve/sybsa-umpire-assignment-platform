from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone


phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)


class LeagueAdmin(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(validators=[phone_regex], max_length=17)
    
    class Meta:
        verbose_name = "League Admin"
        verbose_name_plural = "League Admins"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Coach(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(validators=[phone_regex], max_length=17)
    
    class Meta:
        verbose_name = "Coach"
        verbose_name_plural = "Coaches"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Town(models.Model):
    name = models.CharField(max_length=100, unique=True)
    league_admin = models.ForeignKey(LeagueAdmin, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Town"
        verbose_name_plural = "Towns"
    
    def __str__(self):
        return self.name


class Team(models.Model):
    LEVEL_CHOICES = [
        ('AAA', 'AAA'),
        ('Minors', 'Minors'),
        ('Majors', 'Majors'),
    ]
    
    town = models.ForeignKey(Town, on_delete=models.CASCADE)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    coach = models.ForeignKey(Coach, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        unique_together = ['town', 'level', 'name']
    
    def __str__(self):
        if self.name:
            return f"{self.town} {self.level} - {self.name}"
        return f"{self.town} {self.level}"


class Umpire(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='umpire_profile')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(validators=[phone_regex], max_length=17)
    adult = models.BooleanField(default=False)
    patched = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Umpire"
        verbose_name_plural = "Umpires"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Game(models.Model):
    TIME_CHOICES = [
        ('8:00', '8:00 AM'),
        ('10:15', '10:15 AM'),
        ('12:30', '12:30 PM'),
        ('2:45', '2:45 PM'),
    ]
    
    FIELD_CHOICES = [
        ('A', 'Field A'),
        ('B', 'Field B'),
        ('C', 'Field C'),
        ('D', 'Field D'),
        ('E', 'Field E'),
    ]
    
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_games')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_games')
    date = models.DateField()
    time = models.CharField(max_length=10, choices=TIME_CHOICES)
    field = models.CharField(max_length=1, choices=FIELD_CHOICES)
    
    class Meta:
        verbose_name = "Game"
        verbose_name_plural = "Games"
        unique_together = ['date', 'time', 'field']
        ordering = ['date', 'time', 'field']
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - {self.date} {self.time}"


class UmpireAssignment(models.Model):
    POSITION_CHOICES = [
        ('plate', 'Plate Umpire'),
        ('base', 'Base Umpire'),
        ('solo', 'Solo Umpire'),
    ]
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='assignments')
    umpire = models.ForeignKey(Umpire, on_delete=models.CASCADE, related_name='assignments')
    position = models.CharField(max_length=10, choices=POSITION_CHOICES)
    pay_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Umpire Assignment"
        verbose_name_plural = "Umpire Assignments"
        unique_together = ['game', 'umpire']
    
    def save(self, *args, **kwargs):
        if not self.pay_amount:
            self.pay_amount = self.calculate_pay()
        super().save(*args, **kwargs)
    
    def calculate_pay(self):
        from .utils import get_pay_rate
        return get_pay_rate(self.umpire.patched, self.position)
    
    def __str__(self):
        return f"{self.umpire} - {self.game} ({self.position})"


class UmpirePayment(models.Model):
    umpire = models.ForeignKey(Umpire, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Umpire Payment"
        verbose_name_plural = "Umpire Payments"
        ordering = ['-period_end', 'umpire']
    
    def __str__(self):
        status = "Paid" if self.paid else "Unpaid"
        return f"{self.umpire} - ${self.amount} ({status}) - {self.period_start} to {self.period_end}"


class PayRate(models.Model):
    solo_patched = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('50.00'))
    solo_unpatched = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('40.00'))
    plate_patched = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('35.00'))
    plate_unpatched = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('30.00'))
    base_unpatched = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('25.00'))
    effective_date = models.DateField(default=timezone.now)
    
    class Meta:
        verbose_name = "Pay Rate"
        verbose_name_plural = "Pay Rates"
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"Pay Rates effective {self.effective_date}"


class UmpireAvailability(models.Model):
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('preferred', 'Preferred'),
    ]
    
    TIME_SLOT_CHOICES = [
        ('8:00', '8:00 AM'),
        ('10:15', '10:15 AM'),
        ('12:30', '12:30 PM'),
        ('2:45', '2:45 PM'),
        ('all', 'All Time Slots'),
    ]
    
    umpire = models.ForeignKey(Umpire, on_delete=models.CASCADE, related_name='availabilities')
    date = models.DateField()
    time_slot = models.CharField(max_length=10, choices=TIME_SLOT_CHOICES, default='all')
    status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Umpire Availability"
        verbose_name_plural = "Umpire Availabilities"
        unique_together = ['umpire', 'date', 'time_slot']
        ordering = ['date', 'time_slot', 'umpire']
    
    def __str__(self):
        time_display = self.get_time_slot_display() if self.time_slot != 'all' else 'All Day'
        return f"{self.umpire} - {self.date} {time_display} ({self.get_status_display()})"
    
    @classmethod
    def get_game_dates_with_slots(cls):
        """Get all unique game dates and their time slots."""
        from django.db.models import Count
        games = Game.objects.values('date', 'time').annotate(count=Count('id')).order_by('date', 'time')
        
        # Define the proper time order
        time_order = ['8:00', '10:15', '12:30', '2:45']
        
        dates_with_slots = {}
        for game in games:
            if game['date'] not in dates_with_slots:
                dates_with_slots[game['date']] = []
            if game['time'] not in dates_with_slots[game['date']]:
                dates_with_slots[game['date']].append(game['time'])
        
        # Sort time slots in chronological order
        for date in dates_with_slots:
            dates_with_slots[date].sort(key=lambda x: time_order.index(x) if x in time_order else 999)
        
        return dates_with_slots
