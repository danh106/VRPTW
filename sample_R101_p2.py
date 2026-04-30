# -*- coding: utf-8 -*-
import json
import os
import random
import math
import copy
import time

from gavrptw.core import (
    route_distance,
    feasible,
    plot_routes,
    route_time,
    shape_metric,
    overlap_simple
)

# ================= GREEDY FEASIBLE INITIAL =================
def greedy_initial_solution(instance, dist, capacity):
    customers = [
        int(k.split('_')[1])
        for k in instance
        if k.startswith('customer_')
    ]

    random.shuffle(customers)
    routes = []

    for c in customers:
        inserted = False

        for r in routes:
            for pos in range(len(r) + 1):
                trial = r[:pos] + [c] + r[pos:]
                if feasible(trial, instance, dist, capacity):
                    r.insert(pos, c)
                    inserted = True
                    break
            if inserted:
                break

        if not inserted:
            routes.append([c])

    return routes


# ================= NEIGHBOR =================
def get_neighbor(routes):
    new_routes = copy.deepcopy(routes)

    if len(new_routes) < 2:
        return new_routes

    r1, r2 = random.sample(range(len(new_routes)), 2)

    if not new_routes[r1] or not new_routes[r2]:
        return new_routes

    i = random.randrange(len(new_routes[r1]))
    j = random.randrange(len(new_routes[r2]))

    n1 = new_routes[r1][i]
    n2 = new_routes[r2][j]

    if isinstance(n1, str) or isinstance(n2, str):
        return new_routes

    new_routes[r1][i], new_routes[r2][j] = n2, n1

    return new_routes


# ================= COST =================
def total_cost(routes, dist):
    return sum(route_distance(r, dist) for r in routes)


# ================= SIMULATED ANNEALING =================
def simulated_annealing(
    routes,
    instance,
    dist,
    capacity,
    T0=5000,
    Tmin=1,
    cooling=0.995,
    iter_per_T=100
):
    current = copy.deepcopy(routes)
    best = copy.deepcopy(routes)

    current_cost = total_cost(current, dist)
    best_cost = current_cost

    T = T0

    while T > Tmin:
        for _ in range(iter_per_T):
            new = get_neighbor(current)

            # đảm bảo feasible
            if not all(feasible(r, instance, dist, capacity) for r in new):
                continue

            new_cost = total_cost(new, dist)
            delta = new_cost - current_cost

            if delta < 0 or random.random() < math.exp(-delta / T):
                current = new
                current_cost = new_cost

                if current_cost < best_cost:
                    best = copy.deepcopy(current)
                    best_cost = current_cost

        T *= cooling

    return best


# ================= RUN ONE =================
def run_sa(instance_name, disposal_sites, plot=False):
    start = time.time()

    BASE = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(BASE, 'data', 'json', f'{instance_name}.json')

    with open(path) as f:
        instance = json.load(f)

    dist = instance['distance_matrix']
    capacity = instance['vehicle_capacity']

    # ===== INIT =====
    routes = greedy_initial_solution(instance, dist, capacity)

    # ===== SA =====
    routes = simulated_annealing(routes, instance, dist, capacity)

    # ===== METRICS =====
    total = sum(route_distance(r, dist) for r in routes)
    route_times = [route_time(r, instance, dist) for r in routes]

    RTD = max(route_times) - min(route_times) if route_times else 0
    Sm = shape_metric(routes, instance)
    Nh = overlap_simple(routes, instance)
    CT = round(time.time() - start, 2)

    # ===== PRINT =====
    print("\n" + "="*100)
    print("SA BASELINE RESULT")
    print("="*100)

    for i, r in enumerate(routes):
        d = route_distance(r, dist)
        print(f"Vehicle {i+1}: 0 -> {' -> '.join(map(str, r))} -> 0 | {d:.2f}")

    print("-"*100)
    print(f"Vehicles (Vn): {len(routes)}")
    print(f"Total distance (TD): {total:.2f}")
    print(f"Shape metric (Sm): {Sm:.2f}")
    print(f"Overlap (Nh): {Nh}")
    print(f"Route time deviation (RTD): {RTD:.2f}")
    print(f"Computation time (CT): {CT} s")
    print("="*100)

    if plot:
        plot_routes(routes, instance, disposal_sites)

    return {
        "vehicles": len(routes),
        "distance": total,
        "Sm": Sm,
        "Nh": Nh,
        "RTD": RTD,
        "CT": CT
    }


# ================= BENCHMARK =================
def benchmark(instance_name, disposal_sites, runs=5):
    results = []

    for i in range(runs):
        print(f"\nRUN {i+1}")
        res = run_sa(instance_name, disposal_sites)
        results.append(res)

    # ===== AVERAGE =====
    avg = {
        "vehicles": sum(r["vehicles"] for r in results) / runs,
        "distance": sum(r["distance"] for r in results) / runs,
        "Sm": sum(r["Sm"] for r in results) / runs,
        "Nh": sum(r["Nh"] for r in results) / runs,
        "RTD": sum(r["RTD"] for r in results) / runs,
        "CT": sum(r["CT"] for r in results) / runs,
    }

    print("\n" + "="*100)
    print("SUMMARY SA BASELINE")
    print("="*100)
    print(f"Vehicles avg: {avg['vehicles']:.2f}")
    print(f"Distance avg: {avg['distance']:.2f}")
    print(f"Sm avg: {avg['Sm']:.2f}")
    print(f"Nh avg: {avg['Nh']:.2f}")
    print(f"RTD avg: {avg['RTD']:.2f}")
    print(f"CT avg: {avg['CT']:.2f}")
    print("="*100)


# ================= MAIN =================
if __name__ == "__main__":
    instance_name = "R111"
    disposal_sites = [10, 50, 15, 55, 82, 97]

    benchmark(instance_name, disposal_sites, runs=5)