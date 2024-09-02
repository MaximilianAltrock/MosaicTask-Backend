import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, now

from api.models import Board, CustomUser, JournalEntry, List, Task


class Command(BaseCommand):
    help = 'Creates enhanced dummy data for the task management and mood tracking system'

    def handle(self, *args, **kwargs):
        # Create users
        usernames = ['maximilian', 'bob', 'charlie', 'david', 'eva']
        users = []
        for username in usernames:
            user, created = CustomUser.objects.get_or_create(username=username)
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
            self.stdout.write(
                self.style.SUCCESS(
                    f'{"Created" if created else "Found"} user: {username}'))

        # Create boards
        boards = []
        for i in range(2):
            board = Board.objects.create(name=f"Board {i+1}")
            board.members.set(users)  # All users are members of both boards
            boards.append(board)
            self.stdout.write(
                self.style.SUCCESS(f'Created board: {board.name}'))

        # Create lists and tasks
        task_statuses = ['active', 'completed']
        tasks = []
        for board in boards:
            for i in range(2):  # 2 lists per board
                list_obj = List.objects.create(
                    name=f"List {i+1} in {board.name}", board=board)
                for j in range(5):  # 5 tasks per list
                    status = random.choice(task_statuses)
                    task = Task.objects.create(
                        title=f"Task {j+1} in {list_obj.name}",
                        description=
                        f"Description for Task {j+1} in {list_obj.name}",
                        due_date=now() +
                        timedelta(days=random.randint(-10, 30)),
                        priority=random.choice([1, 2, 3]),
                        complexity=random.choice([1, 2, 3]),
                        list=list_obj,
                        completed=(status == 'completed'))
                    task.assigned_to.set(
                        random.sample(users, k=random.randint(1, len(users))))
                    if status == 'completed':
                        task.completed_at = now() - timedelta(
                            days=random.randint(1, 15))
                        task.save()
                    tasks.append(task)
                    self.stdout.write(
                        self.style.SUCCESS(f'Created task: {task.title}'))

        # Create journal entries
        start_date = now().date() - timedelta(days=60)
        visibility_options = ['private', 'shared', 'public']
        for day in range(61):  # Create entries for the past 60 days
            date = start_date + timedelta(days=day)
            for user in users:
                for _ in range(random.randint(
                        1, 5)):  # 1 to 5 entries per day per user
                    aware_date = make_aware(
                        datetime.combine(date, datetime.min.time()) +
                        timedelta(hours=random.randint(8, 20),
                                  minutes=random.randint(0, 59)))

                    valence = random.uniform(-1, 1)
                    arousal = random.uniform(-1, 1)

                    related_task = random.choice(
                        tasks) if random.random() < 0.7 else None

                    visibility = random.choice(visibility_options)

                    journal_entry = JournalEntry.objects.create(
                        user=user,
                        title=f"Journal entry for {user.username} on {date}",
                        content=
                        f"This is the content of the journal entry for {user.username} on {date}. "
                        f"Today's mood: {'positive' if valence > 0 else 'negative'} "
                        f"with {'high' if arousal > 0 else 'low'} energy.",
                        created_at=aware_date,
                        task=related_task,
                        valence=valence,
                        arousal=arousal,
                        visibility=visibility)

                    if visibility == 'shared':
                        potential_shared_users = list(
                            CustomUser.objects.exclude(id=user.id))
                        shared_users = random.sample(
                            potential_shared_users,
                            k=random.randint(
                                1, min(3, len(potential_shared_users))))
                        journal_entry.shared_with.set(shared_users)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created journal entry: {journal_entry.title}'))

        self.stdout.write(
            self.style.SUCCESS('Successfully created enhanced dummy data'))
