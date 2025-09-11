from django.core.management.base import BaseCommand
from assignments.models import UmpireAssignment
from decimal import Decimal


class Command(BaseCommand):
    help = 'Fix payment amounts for all assignments'

    def handle(self, *args, **options):
        self.stdout.write('Fixing payment amounts for all assignments...')
        
        # Get all assignments with $0.00 payment
        zero_assignments = UmpireAssignment.objects.filter(
            pay_amount=Decimal('0.00'),
            worked_status__in=['assigned', 'worked']
        )
        
        self.stdout.write(f'Found {zero_assignments.count()} assignments with $0.00 payment')
        
        fixed_count = 0
        for assignment in zero_assignments:
            old_amount = assignment.pay_amount
            # The save method will recalculate the payment
            assignment.save()
            
            if assignment.pay_amount != old_amount:
                fixed_count += 1
                self.stdout.write(
                    f'  Fixed: {assignment.umpire} - {assignment.game} '
                    f'({assignment.position}): ${assignment.pay_amount}'
                )
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Fixed {fixed_count} assignments'
        ))
        
        # Show summary
        total_assignments = UmpireAssignment.objects.filter(
            worked_status__in=['assigned', 'worked']
        ).count()
        
        total_with_payment = UmpireAssignment.objects.filter(
            worked_status__in=['assigned', 'worked'],
            pay_amount__gt=0
        ).count()
        
        self.stdout.write(
            f'\nSummary: {total_with_payment}/{total_assignments} '
            f'assignments now have payment amounts'
        )