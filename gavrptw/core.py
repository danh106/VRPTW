# -*- coding: utf-8 -*-
import json
import os
import math
import time
import random
import copy
import matplotlib.pyplot as plt

# ================= NODE =================
def is_ds(node):
    return isinstance(node, str) and node.startswith("DS")

def is_lunch(node):
    return node == "LUNCH"

def get_id(node):
    return int(node.split('_')[1]) if isinstance(node, str) else node


# ================= VISUAL =================
def plot_routes_live(routes, instance, disposal_sites, cost=None):
    plt.clf()
    depot = instance['depart']['coordinates']

    plt.scatter(depot['x'], depot['y'], marker='s', s=120, color='black', label='Depot')

    first = True
    for ds in disposal_sites:
        d = instance[f'customer_{ds}']
        plt.scatter(d['coordinates']['x'], d['coordinates']['y'],
                    marker='X', s=120, color='red',
                    label='Disposal' if first else None)
        first = False

    for i, r in enumerate(routes):
        x, y = [depot['x']], [depot['y']]

        for n in r:
            if is_lunch(n):
                continue

            nid = get_id(n)
            d = instance[f'customer_{nid}']

            x.append(d['coordinates']['x'])
            y.append(d['coordinates']['y'])

            if is_ds(n):
                plt.scatter(x[-1], y[-1], color='red', s=150)

        x.append(depot['x'])
        y.append(depot['y'])

        plt.plot(x, y, marker='o', label=f'Vehicle {i+1}')

    title = "Routing"
    if cost:
        title += f" | Cost: {cost:.2f}"

    plt.title(title)
    if len(routes) <= 10:
        plt.legend()
    plt.grid()
    plt.pause(0.05)


# ================= COST =================
def route_cost(route, instance, dist, capacity,
               unit_cost, init_cost, wait_cost, delay_cost,
               lunch_window, lunch_duration):

    time_now, load, last = 0, 0, 0
    total_dist, wait, delay = 0, 0, 0

    for n in route:

        if is_lunch(n):
            if time_now < lunch_window[0]:
                wait += lunch_window[0] - time_now
                time_now = lunch_window[0]
            if time_now > lunch_window[1]:
                delay += time_now - lunch_window[1]
            time_now += lunch_duration
            continue

        nid = get_id(n)
        d = instance[f'customer_{nid}']

        travel = dist[last][nid]
        total_dist += travel
        time_now += travel

        if time_now < d['ready_time']:
            wait += d['ready_time'] - time_now
            time_now = d['ready_time']

        if time_now > d['due_time']:
            delay += time_now - d['due_time']

        if is_ds(n):
            load = 0
            service = 30
        else:
            load += d['demand']
            service = d['service_time']

        time_now += service
        last = nid

    total_dist += dist[last][0]

    return (total_dist * unit_cost +
            init_cost +
            wait * wait_cost +
            delay * delay_cost)


def solution_cost(routes, *args):
    return sum(route_cost(r, *args) for r in routes)


# ================= FEASIBLE =================
def feasible(route, instance, dist, capacity,
             lunch_window, lunch_duration):

    time_now, load, last = 0, 0, 0
    depot_due = instance['depart']['due_time']

    for n in route:

        if is_lunch(n):
            if time_now < lunch_window[0]:
                time_now = lunch_window[0]
            time_now += lunch_duration
            continue

        nid = get_id(n)
        d = instance[f'customer_{nid}']

        if is_ds(n):
            load = 0
        else:
            load += d['demand']
            if load > capacity:
                return False

        time_now += dist[last][nid]

        if time_now > d['due_time']:
            return False

        service = 30 if is_ds(n) else d['service_time']
        time_now = max(time_now, d['ready_time']) + service
        last = nid

    time_now += dist[last][0]
    return time_now <= depot_due


# ================= SORT + CLUSTER =================
def sort_customers(instance):
    depot = instance['depart']['coordinates']
    nodes = []

    for k in instance:
        if k.startswith('customer_'):
            cid = int(k.split('_')[1])
            d = instance[k]

            angle = math.atan2(
                d['coordinates']['y'] - depot['y'],
                d['coordinates']['x'] - depot['x']
            )
            nodes.append((cid, angle))

    nodes.sort(key=lambda x: x[1])
    return [n[0] for n in nodes]


def sweep_clustering(customers, instance, capacity):
    clusters, cur, load = [], [], 0

    for c in customers:
        d = instance[f'customer_{c}']['demand']

        if load + d <= capacity:
            cur.append(c)
            load += d
        else:
            clusters.append(cur)
            cur = [c]
            load = d

    if cur:
        clusters.append(cur)

    return clusters


# ================= DISPOSAL =================
def best_disposal(prev, next_node, disposal_sites, dist):
    best, best_cost = None, float('inf')

    for ds in disposal_sites:
        cost = dist[prev][ds] + dist[ds][next_node]
        if cost < best_cost:
            best_cost = cost
            best = ds

    return best


# ================= INSERT =================
def best_insertion(route, c, instance, dist, capacity,
                   disposal_sites,
                   *cost_args):

    best_r, best_c = None, float('inf')

    for i in range(len(route)+1):

        trial = route[:i] + [c] + route[i:]

        if feasible(trial, instance, dist, capacity,
                    cost_args[-2], cost_args[-1]):

            cost = route_cost(trial, instance, dist, capacity, *cost_args)

            if cost < best_c:
                best_r, best_c = trial, cost

        else:
            prev = 0 if i == 0 else get_id(route[i-1])
            ds = best_disposal(prev, c, disposal_sites, dist)

            trial = route[:i] + [f"DS_{ds}", c] + route[i:]

            if feasible(trial, instance, dist, capacity,
                        cost_args[-2], cost_args[-1]):

                cost = route_cost(trial, instance, dist, capacity, *cost_args)

                if cost < best_c:
                    best_r, best_c = trial, cost

    return best_r


# ================= BUILD =================
def build_routes(clusters, instance, dist, capacity,
                 disposal_sites, *cost_args):

    routes = []

    for cluster in clusters:
        unvisited = cluster[:]

        while unvisited:
            r = [unvisited.pop(0)]

            while True:
                best = None
                best_r = None
                best_cost = float('inf')

                for c in unvisited:
                    new_r = best_insertion(
                        r, c, instance, dist, capacity,
                        disposal_sites, *cost_args
                    )

                    if new_r:
                        cost = route_cost(new_r, instance, dist, capacity, *cost_args)
                        if cost < best_cost:
                            best, best_r, best_cost = c, new_r, cost

                if best is None:
                    break

                r = best_r
                unvisited.remove(best)

            routes.append(r)

    return routes


# ================= LOCAL SEARCH =================
def relocate(routes, instance, dist, capacity, lw, ld):
    for i in range(len(routes)):
        for j in range(len(routes)):
            if i == j:
                continue
            for k in range(len(routes[i])):
                n = routes[i][k]
                if isinstance(n, str):
                    continue

                r1 = routes[i][:k] + routes[i][k+1:]

                for pos in range(len(routes[j])+1):
                    r2 = routes[j][:pos] + [n] + routes[j][pos:]

                    if feasible(r1, instance, dist, capacity, lw, ld) and \
                       feasible(r2, instance, dist, capacity, lw, ld):
                        routes[i], routes[j] = r1, r2
                        return True
    return False


def swap(routes, instance, dist, capacity, lw, ld):
    for i in range(len(routes)):
        for j in range(i+1, len(routes)):
            for a in range(len(routes[i])):
                for b in range(len(routes[j])):
                    n1, n2 = routes[i][a], routes[j][b]

                    if isinstance(n1, str) or isinstance(n2, str):
                        continue

                    r1, r2 = routes[i][:], routes[j][:]
                    r1[a], r2[b] = n2, n1

                    if feasible(r1, instance, dist, capacity, lw, ld) and \
                       feasible(r2, instance, dist, capacity, lw, ld):
                        routes[i], routes[j] = r1, r2
                        return True
    return False


def vehicle_reduction(routes, instance, dist, capacity, lw, ld):
    routes = sorted(routes, key=lambda r: len(r))

    for i in range(len(routes)):
        removed = routes[i]
        others = [r[:] for j, r in enumerate(routes) if j != i]

        ok = True
        for n in removed:
            if isinstance(n, str):
                continue

            inserted = False
            for r in others:
                for pos in range(len(r)+1):
                    trial = r[:pos] + [n] + r[pos:]
                    if feasible(trial, instance, dist, capacity, lw, ld):
                        r.insert(pos, n)
                        inserted = True
                        break
                if inserted:
                    break

            if not inserted:
                ok = False
                break

        if ok:
            return others

    return routes


# ================= LNS =================
def ruin_recreate(routes, instance, dist, capacity,
                  disposal_sites, *cost_args):

    k = random.randint(1, max(1, len(routes)//2))
    remove_idx = random.sample(range(len(routes)), k)

    removed, remain = [], []

    for i, r in enumerate(routes):
        if i in remove_idx:
            removed += [n for n in r if not isinstance(n, str)]
        else:
            remain.append(r)

    random.shuffle(removed)

    for c in removed:
        best_i, best_r, best_cost = None, None, float('inf')

        for i, r in enumerate(remain):
            new_r = best_insertion(
                r, c, instance, dist, capacity,
                disposal_sites, *cost_args
            )

            if new_r:
                cost = route_cost(new_r, instance, dist, capacity, *cost_args)
                if cost < best_cost:
                    best_i, best_r, best_cost = i, new_r, cost

        if best_i is None:
            remain.append([c])
        else:
            remain[best_i] = best_r

    return remain


# ================= SA =================
def simulated_annealing(routes, instance, dist, capacity,
                        disposal_sites, *cost_args):

    T, cooling = 5000, 0.995

    cur = copy.deepcopy(routes)
    best = copy.deepcopy(routes)

    cur_cost = solution_cost(cur, instance, dist, capacity, *cost_args)
    best_cost = cur_cost

    while T > 1:
        new = ruin_recreate(cur, instance, dist, capacity,
                            disposal_sites, *cost_args)

        new_cost = solution_cost(new, instance, dist, capacity, *cost_args)
        delta = new_cost - cur_cost

        if delta < 0 or random.random() < math.exp(-delta / T):
            cur, cur_cost = new, new_cost

        if cur_cost < best_cost:
            best, best_cost = copy.deepcopy(cur), cur_cost
            plot_routes_live(best, instance, disposal_sites, best_cost)

        T *= cooling

    return best


# ================= MAIN =================
def run_gavrptw(instance_name, disposal_sites,
                unit_cost, init_cost, wait_cost, delay_cost):

    start = time.time()

    BASE = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(BASE, 'data', 'json', f'{instance_name}.json')

    with open(path) as f:
        instance = json.load(f)

    dist = instance['distance_matrix']
    capacity = instance['vehicle_capacity']

    lunch_window = (12*3600, 13*3600)
    lunch_duration = 3600

    cost_args = (
        unit_cost, init_cost, wait_cost, delay_cost,
        lunch_window, lunch_duration
    )

    plt.ion()
    plt.figure(figsize=(8, 8))

    customers = sort_customers(instance)
    clusters = sweep_clustering(customers, instance, capacity)

    routes = build_routes(clusters, instance, dist, capacity,
                          disposal_sites, *cost_args)

    for _ in range(20):
        if not relocate(routes, instance, dist, capacity, lunch_window, lunch_duration):
            break

    for _ in range(20):
        if not swap(routes, instance, dist, capacity, lunch_window, lunch_duration):
            break

    for _ in range(10):
        routes = vehicle_reduction(routes, instance, dist, capacity, lunch_window, lunch_duration)

    routes = simulated_annealing(routes, instance, dist, capacity,
                                 disposal_sites, *cost_args)

    total = solution_cost(routes, instance, dist, capacity, *cost_args)

    print("\n===== FINAL RESULT =====")
    for i, r in enumerate(routes):
        print(f"Vehicle {i+1}: 0 -> {' -> '.join(map(str,r))} -> 0")

    print(f"\nTotal cost: {total:.2f}")
    print(f"Vehicles: {len(routes)}")
    print(f"Time: {round(time.time() - start, 2)} s")

    plt.ioff()
    plt.show()

    return routes