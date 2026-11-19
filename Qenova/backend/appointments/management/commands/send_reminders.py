import time

from django.core.management.base import BaseCommand

from appointments.reminders import run_reminders


class Command(BaseCommand):
    help = "Send 24-hour and 1-hour appointment reminders by email and SMS."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Keep running and check every --interval seconds.")
        parser.add_argument("--interval", type=int, default=60, help="Seconds between checks with --loop.")

    def handle(self, *args, **options):
        try:
            while True:
                sent = run_reminders()
                self.stdout.write(f"Reminders sent - 24h: {sent['24h']}, 1h: {sent['1h']}")
                if not options["loop"]:
                    break
                time.sleep(max(10, options["interval"]))
        except KeyboardInterrupt:
            self.stdout.write("Stopped.")
