import uuid

from locust import HttpUser, between, task


class FlashSaleUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a Locust user starts before any task is scheduled."""
        self.email = f"user_{uuid.uuid4()}@example.com"
        self.password = "strongpassword123"
        self.token = None
        self.challenge_id = None
        self.answer = None

        # 1. Signup
        signup_res = self.client.post(
            "/auth/signup",
            json={
                "email": self.email,
                "password": self.password,
                "full_name": "Test User",
            },
        )

        # 2. Login
        login_res = self.client.post(
            "/auth/login", json={"email": self.email, "password": self.password}
        )

        if login_res.status_code == 200:
            self.token = login_res.json()["token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

        # 3. Get Challenge
        challenge_res = self.client.get(
            "/buy/challenge", headers=getattr(self, "headers", {})
        )
        if challenge_res.status_code == 200:
            data = challenge_res.json()
            self.challenge_id = data["challenge_id"]
            question = data["question"]
            try:
                # "What is X + Y?"
                parts = question.replace("?", "").split(" ")
                num1 = int(parts[2])
                num2 = int(parts[4])
                self.answer = num1 + num2
            except Exception:
                self.answer = 0

    @task
    def attempt_purchase(self):
        if not getattr(self, "token", None):
            return

        payload = {
            "user_id": "dummy",
            "item_id": ["1"],
            "challenge_answer": self.answer,
        }

        # We can simulate spamming the button
        self.client.post("/buy/", json=payload, headers=self.headers)
