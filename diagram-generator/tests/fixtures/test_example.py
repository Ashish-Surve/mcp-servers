"""Example Python code for testing diagram generation."""

from enum import Enum
from typing import List, Optional


class Priority(Enum):
    """Task priority levels."""

    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class Status(Enum):
    """Task status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class BaseModel:
    """Base class for all models."""

    def __init__(self):
        self.id = None
        self.created_at = None


class Task(BaseModel):
    """Represents a task in the system."""

    def __init__(self, title: str, description: str, priority: Priority):
        super().__init__()
        self.title = title
        self.description = description
        self.priority = priority
        self.status = Status.TODO
        self.assignee = None

    def assign(self, user: str):
        """Assign task to a user."""
        self.assignee = user

    def complete(self):
        """Mark task as complete."""
        self.status = Status.DONE

    def is_complete(self) -> bool:
        """Check if task is complete."""
        return self.status == Status.DONE


class Project(BaseModel):
    """Represents a project containing tasks."""

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.tasks = []

    def add_task(self, task: Task):
        """Add a task to the project."""
        self.tasks.append(task)

    def get_tasks(self) -> List[Task]:
        """Get all tasks in the project."""
        return self.tasks

    def get_completed_tasks(self) -> List[Task]:
        """Get completed tasks."""
        return [t for t in self.tasks if t.is_complete()]


class TaskRepository:
    """Repository for managing tasks."""

    def __init__(self):
        self.tasks = {}

    def save(self, task: Task):
        """Save a task."""
        self.tasks[task.id] = task

    def find_by_id(self, task_id: str) -> Optional[Task]:
        """Find task by ID."""
        return self.tasks.get(task_id)

    def find_all(self) -> List[Task]:
        """Get all tasks."""
        return list(self.tasks.values())


class TaskService:
    """Service for task operations."""

    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def create_task(self, title: str, description: str, priority: Priority) -> Task:
        """Create a new task."""
        task = Task(title, description, priority)
        self.repository.save(task)
        return task

    def complete_task(self, task_id: str):
        """Complete a task."""
        task = self.repository.find_by_id(task_id)
        if task:
            task.complete()
            self.repository.save(task)
