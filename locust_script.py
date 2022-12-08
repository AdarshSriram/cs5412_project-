import time
from locust_script import HttpUser, task, between
import locust_plugins
from random import randint


class QuickstartUser(HttpUser):
# wait_time = between(1, 5)

    @task
    def hello_world(self):
        time.sleep(randint(1,4))

        self.client.get("https://locationmarketplacedev.azurewebsites.net/local-feed")