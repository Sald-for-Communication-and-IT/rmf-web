from tortoise.fields import CharField, DatetimeField, JSONField
from tortoise.models import Model


class TaskState(Model):
    id_ = CharField(255, pk=True, source_field="id")
    data = JSONField()
    category = CharField(255, null=True, index=True)
    unix_millis_start_time = DatetimeField(null=True, index=True)
    unix_millis_finish_time = DatetimeField(null=True, index=True)


class TaskEventLog(Model):
    task_id = CharField(255, pk=True)
    data = JSONField()
