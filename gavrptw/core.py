# -*- coding: utf-8 -*-
import json
import os
import math
import time
import random
import copy
import matplotlib.pyplot as plt
# ================= COST =================
def route_distance(route, dist):
    total, last = 0, 0
    for node in route:
        nid = int(node.split('_')[1]) if isinstance(node, str) else node
        total += dist[last][nid]
        last = nid
    total += dist[last][0]
    return total


# ================= ROUTE TIME =================
def route_time(route, instance, dist):
    time_now, last = 0, 0

    for node in route:
        nid = int(node.split('_')[1]) if isinstance(node, str) else node
        data = instance[f'customer_{nid}']

        time_now += dist[last][nid]

        if time_now < data['ready_time']:
            time_now = data['ready_time']

        service = 30 if isinstance(node, str) else data['service_time']
        time_now += service

        last = nid

    time_now += dist[last][0]
    return time_now


# ================= SHAPE METRIC =================
def shape_metric(routes, instance):
    total = 0

    for route in routes:
        xs, ys = [], []

        for node in route:
            if isinstance(node, str):
                continue
            data = instance[f'customer_{node}']
            xs.append(data['coordinates']['x'])
            ys.append(data['coordinates']['y'])

        if not xs:
            continue

        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        for node in route:
            if isinstance(node, str):
                continue
            data = instance[f'customer_{node}']
            dx = data['coordinates']['x'] - cx
            dy = data['coordinates']['y'] - cy
            total += math.sqrt(dx*dx + dy*dy)

    return total


# ================= OVERLAP (SIMPLE) =================
def overlap_simple(routes, instance):
    boxes = []

    for route in routes:
        xs, ys = [], []

        for node in route:
            if isinstance(node, str):
                continue
            data = instance[f'customer_{node}']
            xs.append(data['coordinates']['x'])
            ys.append(data['coordinates']['y'])

        if xs:
            boxes.append((min(xs), max(xs), min(ys), max(ys)))

    count = 0
    for i in range(len(boxes)):
        for j in range(i+1, len(boxes)):
            a = boxes[i]
            b = boxes[j]

            if (a[0] <= b[1] and a[1] >= b[0] and
                a[2] <= b[3] and a[3] >= b[2]):
                count += 1

    return count
# ================= PLOT ROUTES =================
def plot_routes(routes, instance, disposal_sites):
    import matplotlib.pyplot as plt

    depot = instance['depart']['coordinates']

    plt.figure(figsize=(8, 8))

    # ===== DEPOT =====
    plt.scatter(depot['x'], depot['y'], marker='s', s=100, label='Depot')

    # ===== DISPOSAL SITES =====
    # ===== DISPOSAL SITES =====
    first = True
    for ds in disposal_sites:
        data = instance[f'customer_{ds}']
        plt.scatter(
            data['coordinates']['x'],
            data['coordinates']['y'],
            marker='x',
            s=80,
            color='red',
            label='Disposal' if first else None
        )
        first = False

    # ===== LEGEND =====
    plt.legend()

    # ===== ROUTES =====
    for idx, route in enumerate(routes):
        x = [depot['x']]
        y = [depot['y']]

        for node in route:
            if isinstance(node, str):
                nid = int(node.split('_')[1])
                data = instance[f'customer_{nid}']
            else:
                data = instance[f'customer_{node}']

            x.append(data['coordinates']['x'])
            y.append(data['coordinates']['y'])

        x.append(depot['x'])
        y.append(depot['y'])

        plt.plot(x, y, marker='o', label=f'Vehicle {idx+1}')

    plt.title("Vehicle Routes with Disposal Sites")
    plt.xlabel("X")
    plt.ylabel("Y")

    if len(routes) <= 10:
        plt.legend()

    plt.grid()
    plt.show()

# ================= FEASIBLE =================
def feasible(route, instance, dist, capacity):
    time_now, load, last = 0, 0, 0
    depot_due = instance['depart']['due_time']

    for node in route:
        nid = int(node.split('_')[1]) if isinstance(node, str) else node
        data = instance[f'customer_{nid}']

        if isinstance(node, str):
            load = 0
        else:
            load += data['demand']
            if load > capacity:
                return False

        time_now += dist[last][nid]
        if time_now > data['due_time']:
            return False

        service = 30 if isinstance(node, str) else data['service_time']
        time_now = max(time_now, data['ready_time']) + service
        last = nid

    time_now += dist[last][0]
    return time_now <= depot_due


# ================= SORT =================
def sort_customers(instance):
    depot = instance['depart']['coordinates']
    nodes = []

    for k in instance:
        if k.startswith('customer_'):
            cid = int(k.split('_')[1])
            data = instance[k]

            angle = math.atan2(
                data['coordinates']['y'] - depot['y'],
                data['coordinates']['x'] - depot['x']
            )

            nodes.append((cid, angle))

    nodes.sort(key=lambda x: x[1])
    return [n[0] for n in nodes]


# ================= CLUSTER =================
def sweep_clustering(customers, instance, capacity):
    clusters = []
    current, load = [], 0

    for c in customers:
        d = instance[f'customer_{c}']['demand']
        if load + d <= capacity:
            current.append(c)
            load += d
        else:
            clusters.append(current)
            current = [c]
            load = d

    if current:
        clusters.append(current)

    return clusters


# ================= EXTENDED INSERTION =================
def best_insertion(route, customer, instance, dist, capacity, disposal_sites):
    best_cost = float('inf')
    best_route = None

    for i in range(len(route)+1):
        trial = route[:i] + [customer] + route[i:]
        if feasible(trial, instance, dist, capacity):
            cost = route_distance(trial, dist)
            if cost < best_cost:
                best_cost = cost
                best_route = trial

        for ds in disposal_sites:
            trial = route[:i] + [f"DS_{ds}", customer] + route[i:]
            if feasible(trial, instance, dist, capacity):
                cost = route_distance(trial, dist)
                if cost < best_cost:
                    best_cost = cost
                    best_route = trial

    return best_route


def build_routes_cluster(cluster, instance, dist, capacity, disposal_sites):
    unvisited = cluster[:]
    routes = []

    while unvisited:
        route = [unvisited.pop(0)]

        while True:
            best_choice = None
            best_route = None
            best_cost = float('inf')

            for c in unvisited:
                new_route = best_insertion(route, c, instance, dist, capacity, disposal_sites)
                if new_route:
                    cost = route_distance(new_route, dist)
                    if cost < best_cost:
                        best_cost = cost
                        best_choice = c
                        best_route = new_route

            if best_choice is None:
                break

            route = best_route
            unvisited.remove(best_choice)

        routes.append(route)

    return routes


def build_routes(clusters, instance, dist, capacity, disposal_sites):
    routes = []
    for cluster in clusters:
        routes += build_routes_cluster(cluster, instance, dist, capacity, disposal_sites)
    return routes


# ================= RELOCATE =================
def relocate(routes, instance, dist, capacity):
    for i in range(len(routes)):
        for j in range(len(routes)):
            if i == j:
                continue
            for k in range(len(routes[i])):
                node = routes[i][k]
                if isinstance(node, str):
                    continue

                r1 = routes[i][:k] + routes[i][k+1:]

                for pos in range(len(routes[j])+1):
                    r2 = routes[j][:pos] + [node] + routes[j][pos:]

                    if feasible(r1, instance, dist, capacity) and feasible(r2, instance, dist, capacity):
                        routes[i], routes[j] = r1, r2
                        return True
    return False


# ================= SWAP =================
def swap(routes, instance, dist, capacity):
    for i in range(len(routes)):
        for j in range(i+1, len(routes)):
            for a in range(len(routes[i])):
                for b in range(len(routes[j])):
                    n1, n2 = routes[i][a], routes[j][b]

                    if isinstance(n1, str) or isinstance(n2, str):
                        continue

                    r1 = routes[i][:]
                    r2 = routes[j][:]
                    r1[a], r2[b] = n2, n1

                    if feasible(r1, instance, dist, capacity) and feasible(r2, instance, dist, capacity):
                        routes[i], routes[j] = r1, r2
                        return True
    return False


# ================= VEHICLE REDUCTION =================
def vehicle_reduction(routes, instance, dist, capacity):
    routes = sorted(routes, key=lambda r: route_distance(r, dist))

    for i in range(len(routes)):
        removed = routes[i]
        others = [r[:] for j, r in enumerate(routes) if j != i]

        success = True
        for node in removed:
            if isinstance(node, str):
                continue

            inserted = False
            for r in others:
                for pos in range(len(r)+1):
                    trial = r[:pos] + [node] + r[pos:]
                    if feasible(trial, instance, dist, capacity):
                        r.insert(pos, node)
                        inserted = True
                        break
                if inserted:
                    break

            if not inserted:
                success = False
                break

        if success:
            return others

    return routes


# ================= RUIN & RECREATE =================
def ruin_recreate(routes, instance, dist, capacity, disposal_sites):
    routes_sorted = sorted(routes, key=lambda r: route_distance(r, dist), reverse=True)
    remove_routes = routes_sorted[:random.randint(1, min(2, len(routes)))]

    remaining = [r[:] for r in routes if r not in remove_routes]

    unassigned = []
    for r in remove_routes:
        for n in r:
            if not isinstance(n, str):
                unassigned.append(n)

    for c in unassigned:
        best_idx = None
        best_route = None
        best_cost = float('inf')

        for i, r in enumerate(remaining):
            new_r = best_insertion(r, c, instance, dist, capacity, disposal_sites)
            if new_r:
                cost = route_distance(new_r, dist)
                if cost < best_cost:
                    best_cost = cost
                    best_idx = i
                    best_route = new_r

        if best_idx is None:
            remaining.append([c])
        else:
            remaining[best_idx] = best_route

    return remaining


# ================= SIMULATED ANNEALING =================
def simulated_annealing(routes, instance, dist, capacity, disposal_sites):
    T = 1000
    cooling = 0.95

    def total_cost(rts):
        return sum(route_distance(r, dist) for r in rts)

    current = copy.deepcopy(routes)
    best = copy.deepcopy(routes)

    current_cost = total_cost(current)
    best_cost = current_cost

    while T > 1:
        new = ruin_recreate(current, instance, dist, capacity, disposal_sites)
        new_cost = total_cost(new)

        delta = new_cost - current_cost

        if delta < 0 or random.random() < math.exp(-delta / T):
            current = new
            current_cost = new_cost

        if current_cost < best_cost:
            best = copy.deepcopy(current)
            best_cost = current_cost

        T *= cooling

    return best


# ================= MAIN =================
def run_gavrptw(instance_name, disposal_sites, unit_cost, init_cost, wait_cost, delay_cost):
    _ = unit_cost, init_cost, wait_cost, delay_cost

    start = time.time()

    BASE = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(BASE, 'data', 'json', f'{instance_name}.json')

    with open(path) as f:
        instance = json.load(f)

    dist = instance['distance_matrix']
    capacity = instance['vehicle_capacity']

    customers = sort_customers(instance)
    clusters = sweep_clustering(customers, instance, capacity)

    routes = build_routes(clusters, instance, dist, capacity, disposal_sites)

    for _ in range(20):
        if not relocate(routes, instance, dist, capacity):
            break

    for _ in range(20):
        if not swap(routes, instance, dist, capacity):
            break

    for _ in range(10):
        routes = vehicle_reduction(routes, instance, dist, capacity)

    routes = simulated_annealing(routes, instance, dist, capacity, disposal_sites)

    # ===== OUTPUT ROUTES =====
    total = 0
    print("\n" + "="*100)
    print(f"{'XE':<5} | {'QUÃNG ĐƯỜNG':<12} | TUYẾN")
    print("-"*100)

    for i, r in enumerate(routes):
        d = route_distance(r, dist)
        total += d
        print(f"{i+1:<5} | {d:<12.2f} | 0 -> {' -> '.join(map(str,r))} -> 0")

    print("-"*100)
    print(f"TỔNG: {len(routes)} xe | Total distance = {total:.2f}")
    print("="*100)

    # ===== METRICS =====
    CT = round(time.time() - start, 2)

    route_times = [route_time(r, instance, dist) for r in routes]
    RTD = max(route_times) - min(route_times) if route_times else 0

    Sm = shape_metric(routes, instance)
    Nh = overlap_simple(routes, instance)

    print("\nKẾT QUẢ (Table 3 metrics)")
    print("-"*100)
    print(f"Số xe (Vn): {len(routes)}")
    print(f"Tổng quãng đường (TD): {total:.2f}")
    print(f"Shape metric (Sm): {Sm:.2f}")
    print(f"Overlap (Nh): {Nh}")
    print(f"Route time deviation (RTD): {RTD:.2f}")
    print(f"Computation time (CT): {CT} s")
    print("="*100)
    
    plot_routes(routes, instance, disposal_sites)

    return routes