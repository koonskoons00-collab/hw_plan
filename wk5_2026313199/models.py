import json
import os
from datetime import datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assignments.json")


class Assignment:
    def __init__(self, subject, title, due_date, due_time="23:59", completed=False, item_id=None):
        self.id = item_id or int(datetime.now().timestamp() * 1000)
        self.subject = subject.strip()
        self.title = title.strip()
        self.due_date = due_date.strip()
        self.due_time = due_time.strip() if due_time.strip() else "23:59"
        self.completed = bool(completed)

    @property
    def due_datetime(self):
        try:
            return datetime.strptime(f"{self.due_date} {self.due_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            return datetime.max

    def is_urgent(self):
        if self.completed:
            return False
        diff = (self.due_datetime - datetime.now()).total_seconds()
        return diff <= 3 * 86400  # 3일(72시간) 이내이거나 지난 미완료 과제

    def time_remaining_str(self):
        if self.completed:
            return "완료"
        now = datetime.now()
        diff = self.due_datetime - now
        total_sec = diff.total_seconds()

        if total_sec < 0:
            past_sec = abs(total_sec)
            past_days = int(past_sec // 86400)
            past_hours = int(past_sec // 3600)
            return f"마감 기한 지남 ({past_days}일 전)" if past_days > 0 else f"마감 시간 지남 ({past_hours}시간 전)"

        days = int(total_sec // 86400)
        hours = int((total_sec % 86400) // 3600)
        minutes = int((total_sec % 3600) // 60)
        if days == 0:
            return f"오늘 마감 ({hours}시간 {minutes}분 남음)"
        elif days == 1:
            return f"내일 마감 (D-1, {hours}시간 남음)"
        return f"D-{days} ({days}일 {hours}시간 남음)"

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "title": self.title,
            "due_date": self.due_date,
            "due_time": self.due_time,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            subject=data.get("subject", ""),
            title=data.get("title", ""),
            due_date=data.get("due_date", ""),
            due_time=data.get("due_time", "23:59"),
            completed=data.get("completed", False),
            item_id=data.get("id"),
        )


class AssignmentManager:
    def __init__(self, filepath=DATA_FILE):
        self.filepath = filepath
        self.assignments = []
        self.load()

    def load(self):
        self.assignments.clear()
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.assignments = [Assignment.from_dict(item) for item in data]
            except Exception:
                self.assignments = []

    def save(self):
        data = [a.to_dict() for a in self.assignments]
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, subject, title, due_date, due_time="23:59"):
        item = Assignment(subject, title, due_date, due_time)
        self.assignments.append(item)
        self.save()
        return item

    def update(self, item_id, subject, title, due_date, due_time):
        for item in self.assignments:
            if item.id == item_id:
                item.subject = subject.strip()
                item.title = title.strip()
                item.due_date = due_date.strip()
                item.due_time = due_time.strip()
                self.save()
                return True
        return False

    def delete(self, item_id):
        self.assignments = [a for a in self.assignments if a.id != item_id]
        self.save()

    def toggle_complete(self, item_id):
        for item in self.assignments:
            if item.id == item_id:
                item.completed = not item.completed
                self.save()
                return item
        return None

    def get_active(self, date_filter=None):
        items = [a for a in self.assignments if not a.completed]
        if date_filter:
            items = [a for a in items if a.due_date == date_filter]
        return sorted(items, key=lambda a: a.due_datetime)

    def get_completed(self):
        items = [a for a in self.assignments if a.completed]
        return sorted(items, key=lambda a: a.due_datetime, reverse=True)

    def get_urgent(self):
        return [a for a in self.get_active() if a.is_urgent()]

    def get_due_count_map(self):
        counts = {}
        for a in self.get_active():
            counts[a.due_date] = counts.get(a.due_date, 0) + 1
        return counts
