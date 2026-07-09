from locust import HttpUser, task, between
import random

class StressUser(HttpUser):
    # No wait time, hammer the endpoint!
    wait_time = between(0, 0)
    
    @task
    def attempt_purchase(self):
        # 1M users to avoid duplicate locks slowing down the RPS
        user_id = str(random.randint(1, 1000000))
        payload = {
            "user_id": user_id,
            "item_id": "1",
        }
        self.client.post("/buy/stress", json=payload)
