# # -*- coding: utf-8 -*-
# import json
# import os
# import math
# import matplotlib.pyplot as plt

# def find_nearest_disposal(last_node_id, disposal_sites, dist_matrix):
#     """Tìm bãi đổ rác gần nhất từ vị trí hiện tại"""
#     return min(disposal_sites, key=lambda ds: dist_matrix[last_node_id][ds])

# def visualize_routes(instance, all_routes, disposal_sites):
#     """Vẽ biểu đồ lộ trình bằng Matplotlib"""
#     plt.figure(figsize=(12, 9))
#     cust_x = [instance[k]['coordinates']['x'] for k in instance if k.startswith('customer_')]
#     cust_y = [instance[k]['coordinates']['y'] for k in instance if k.startswith('customer_')]
#     plt.scatter(cust_x, cust_y, c='silver', s=30, alpha=0.5, label='Khách hàng')

#     depot_x, depot_y = instance['depart']['coordinates']['x'], instance['depart']['coordinates']['y']
#     plt.plot(depot_x, depot_y, 'rs', markersize=12, label='Depot (Kho)')

#     for ds_id in disposal_sites:
#         ds_data = instance[f'customer_{ds_id}']
#         plt.plot(ds_data['coordinates']['x'], ds_data['coordinates']['y'], 'g^', markersize=10)
#     plt.plot([], [], 'g^', label='Bãi đổ rác (DS)')

#     cmap = plt.get_cmap('tab20')
#     for idx, route in enumerate(all_routes):
#         color = cmap(idx % 20)
#         path_x, path_y = [depot_x], [depot_y]
#         for node in route:
#             node_id = int(node.split('_')[1]) if isinstance(node, str) else int(node)
#             target = instance[f'customer_{node_id}']
#             path_x.append(target['coordinates']['x'])
#             path_y.append(target['coordinates']['y'])
#         path_x.append(depot_x)
#         path_y.append(depot_y)
#         plt.plot(path_x, path_y, '-', color=color, linewidth=2, alpha=0.8)

#     plt.title("Tối ưu kết hợp: Time Window + Polar Angle (Kim et al. 2006)", fontsize=14)
#     plt.grid(True, linestyle=':', alpha=0.5)
#     plt.show()

# def run_gavrptw(instance_name, disposal_sites=[10, 50], **kwargs):
#     # 1. Load Data
#     BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
#     json_path = os.path.join(BASE_DIR, 'data', 'json', f'{instance_name}.json')
#     with open(json_path, 'r') as f:
#         instance = json.load(f)

#     dist_matrix = instance['distance_matrix']
#     capacity = instance['vehicle_capacity']
#     depot_due_time = instance['depart']['due_time']
#     depot_coords = instance['depart']['coordinates']
#     disposal_service_time = 30 

#     # 2. SẮP XẾP KẾT HỢP (DUE TIME & POLAR ANGLE)
#     cust_keys = [k for k in instance.keys() if k.startswith('customer_')]
#     customer_list = []
#     for k in cust_keys:
#         cid = int(k.split('_')[1])
#         c_data = instance[k]
#         # Tính góc để đảm bảo tính phân cụm địa lý
#         dx = c_data['coordinates']['x'] - depot_coords['x']
#         dy = c_data['coordinates']['y'] - depot_coords['y']
#         angle = math.atan2(dy, dx)
#         customer_list.append({
#             'id': cid, 
#             'angle': angle, 
#             'due_time': c_data['due_time']
#         })

#     # Sắp xếp: Ưu tiên thời gian (Due Time), nếu trùng thì xét góc (Angle)
#     customer_list.sort(key=lambda x: (x['due_time'], x['angle']))
#     unvisited = [c['id'] for c in customer_list]

#     all_routes = []

#     # 3. LẬP LỘ TRÌNH (EXTENDED INSERTION)
#     while unvisited:
#         route = []
#         current_load = 0
#         current_time = 0
#         last_node = 0
        
#         i = 0
#         # Tầm nhìn (Look-ahead): Cho phép xe tìm kiếm trong toàn bộ danh sách khách còn lại
#         while i < len(unvisited):
#             candidate = unvisited[i]
#             data = instance[f'customer_{candidate}']
            
#             can_serve = False
#             used_ds = False
#             arrival_actual = 0
#             selected_ds = None

#             # TH1: Chèn trực tiếp (Nếu còn tải trọng)
#             if current_load + data['demand'] <= capacity:
#                 arr = current_time + dist_matrix[last_node][candidate]
#                 fin = max(arr, data['ready_time']) + data['service_time']
#                 if arr <= data['due_time'] and fin + dist_matrix[candidate][0] <= depot_due_time:
#                     can_serve, arrival_actual = True, arr

#             # TH2: Chèn mở rộng (Ghé bãi đổ rác DS)
#             if not can_serve:
#                 ds_id = find_nearest_disposal(last_node, disposal_sites, dist_matrix)
#                 arr_ds = current_time + dist_matrix[last_node][ds_id] + disposal_service_time + dist_matrix[ds_id][candidate]
#                 fin = max(arr_ds, data['ready_time']) + data['service_time']
#                 if arr_ds <= data['due_time'] and fin + dist_matrix[candidate][0] <= depot_due_time:
#                     can_serve, used_ds, arrival_actual, selected_ds = True, True, arr_ds, ds_id

#             if can_serve:
#                 if used_ds:
#                     route.append(f"DS_{selected_ds}")
#                     current_load = 0 # Đổ rác xong xe trống tải
                
#                 current_time = max(arrival_actual, data['ready_time']) + data['service_time']
#                 current_load += data['demand']
#                 last_node = candidate
#                 route.append(candidate)
#                 unvisited.pop(i)
#                 # Reset i về 0 để tìm khách hàng phù hợp nhất tiếp theo trong danh sách đã xếp
#                 i = 0 
#             else:
#                 # Nếu khách hàng này không khả thi, thử người tiếp theo
#                 i += 1
        
#         if route:
#             all_routes.append(route)

#     # 4. IN BÁO CÁO LỘ TRÌNH
#     print("\n" + "="*60)
#     print(f"KẾT QUẢ TỐI ƯU (TIME WINDOW + SWEEP ORDERING)")
#     print(f"TỔNG SỐ XE: {len(all_routes)}")
#     print("="*60)
#     for idx, r in enumerate(all_routes):
#         print(f"Xe {idx+1:02d}: 0 -> {' -> '.join(map(str, r))} -> 0")
#     print("="*60 + "\n")

#     visualize_routes(instance, all_routes, disposal_sites)
#     return all_routes