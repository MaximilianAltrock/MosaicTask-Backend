import random
from datetime import timedelta
from itertools import product

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Board, CustomUser, JournalEntry, List, Task


@receiver(post_save, sender=CustomUser)
def create_user_data(sender, instance, created, **kwargs):
    if created:
        # Create a board
        board = Board.objects.create(name=f"{instance.username}'s Board")
        board.members.add(instance)

        # Create lists
        lists = ['To Do', 'In Progress', 'Done']
        created_lists = []
        for i, list_name in enumerate(lists):
            created_lists.append(
                List.objects.create(name=list_name, board=board, position=i))

        # Create tasks for each priority and complexity combination
        task_titles = [
            "Implement user authentication", "Design database schema",
            "Create API endpoints", "Write unit tests",
            "Set up CI/CD pipeline", "Optimize database queries",
            "Implement caching mechanism", "Create user dashboard",
            "Integrate third-party API", "Implement real-time notifications",
            "Refactor legacy code", "Implement data visualization",
            "Optimize front-end performance", "Implement search functionality",
            "Set up monitoring and logging"
        ]

        priorities = [1, 2, 3]
        complexities = [1, 2, 3]

        for i, (priority,
                complexity) in enumerate(product(priorities, complexities)):
            due_date = timezone.now() + timedelta(days=random.randint(1, 30))
            task = Task.objects.create(
                title=task_titles[i % len(task_titles)],
                description=
                f"Description for {task_titles[i % len(task_titles)]}",
                due_date=due_date,
                priority=priority,
                complexity=complexity,
                list=random.choice(created_lists),
                position=i)
            task.assigned_to.add(instance)

            # Create journal entries for each task
            for _ in range(random.randint(2, 5)):
                create_journal_entry(instance, task)

        print(f"Created initial data for user {instance.username}")


def create_journal_entry(user, task):
    entry_date = timezone.now() - timedelta(days=random.randint(1, 14))
    valence = random.uniform(-1, 1)
    arousal = random.uniform(-1, 1)

    mood_description = get_mood_description(valence, arousal)

    JournalEntry.objects.create(
        user=user,
        task=task,
        title=f"Update on {task.title}",
        content=
        f"Working on {task.title}. Task priority: {task.priority}, complexity: {task.complexity}. Feeling {mood_description}.",
        created_at=entry_date,
        valence=valence,
        arousal=arousal,
        visibility=random.choice(['private', 'shared', 'public']))


def get_mood_description(valence, arousal):
    if valence > 0.5:
        if arousal > 0.5:
            return "excited and positive"
        elif arousal < -0.5:
            return "calm and content"
        else:
            return "generally good"
    elif valence < -0.5:
        if arousal > 0.5:
            return "angry or frustrated"
        elif arousal < -0.5:
            return "sad or depressed"
        else:
            return "generally negative"
    else:
        if arousal > 0.5:
            return "alert but neutral"
        elif arousal < -0.5:
            return "tired or bored"
        else:
            return "neutral"
