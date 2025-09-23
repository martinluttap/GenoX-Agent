from locust import HttpUser, task, between, events
import time, csv, threading

# Thread-safe CSV writer for per-request latency
lock = threading.Lock()
csv_file = open("latency_logs.csv", "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["timestamp", "method", "endpoint", "response_time_ms", "status_code"])

@events.request.add_listener
def log_request(name, response_time, response_length, response, context, exception, **kwargs):
    with lock:
        csv_writer.writerow([
            int(time.time() * 1000),
            response.request.method if response else "NA",
            name,
            response_time,
            response.status_code if response else "ERR"
        ])
        csv_file.flush()


class SockShopUser(HttpUser):
    wait_time = between(1, 3)

    @task(2)
    def view_home(self):
        self.client.get("/", name="/")

    @task(1)
    def view_category_page(self):
        self.client.get("/category.html", name="/category.html")

    @task(1)
    def view_basket_page(self):
        self.client.get("/basket.html", name="/basket.html")

    @task(2)
    def view_fixed_product_detail(self):
        self.client.get(
            "/detail.html?id=510a0d7e-8e83-4193-b483-e27e09ddc34d",
            name="/detail.html"
        )

