from django.db import models


class History(models.Model):
    user_id = models.IntegerField()  # Or ForeignKey to User if linked to Django auth
    order_id = models.AutoField(primary_key=True)  # Auto increment ID
    url = models.URLField(max_length=500)  # URL storage
    created_at = models.DateTimeField(auto_now_add=True)  # Auto add timestamp
    data = models.JSONField()

    def __str__(self):
        return f"Order ID : {self.order_id} ( by User {self.user_id} )"