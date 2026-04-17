import json
import matplotlib.pyplot as plt
import random

with open("data/json/R101.json") as f:
    data = json.load(f)

customers = {}

for key in data:
    if key.startswith("customer_"):
        cid = int(key.split("_")[1])
        customers[cid] = data[key]["coordinates"]

# depot (trong dataset Solomon depot thường là 0,50)
depot = {"x": 40, "y": 50}

# ví dụ route (thay bằng route GA tìm được)
routes = [
    [0, 5, 12, 18, 0],
    [0, 7, 9, 11, 0],
    [0, 3, 14, 21, 0]
]

plt.figure(figsize=(8,6))

# vẽ khách hàng
for cid in customers:
    x = customers[cid]["x"]
    y = customers[cid]["y"]
    plt.scatter(x, y)
    plt.text(x, y, str(cid), fontsize=8)

# vẽ depot
plt.scatter(depot["x"], depot["y"], marker="s", s=200)
plt.text(depot["x"], depot["y"], "Depot")

# màu cho từng xe
colors = ["red","blue","green","purple","orange","black"]

# vẽ route
for i,route in enumerate(routes):

    color = colors[i % len(colors)]

    rx = []
    ry = []

    for node in route:

        if node == 0:
            rx.append(depot["x"])
            ry.append(depot["y"])
        else:
            rx.append(customers[node]["x"])
            ry.append(customers[node]["y"])

    plt.plot(rx, ry, color=color, linewidth=2,label=f"Vehicle {i+1}")

plt.title("VRPTW Solution")
plt.xlabel("X")
plt.ylabel("Y")
plt.legend()

plt.show()